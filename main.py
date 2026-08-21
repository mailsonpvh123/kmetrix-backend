from fastapi import FastAPI, Depends, HTTPException, Security, status, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from datetime import datetime, timezone
from typing import Optional, List
import secrets
import hashlib 
import math

from database import engine, Base, get_db
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="KMetrix API", version="1.3.1")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def get_current_driver(
    api_key_header: str = Security(api_key_header), 
    db: Session = Depends(get_db)
) -> models.Driver:
    driver = db.query(models.Driver).filter(models.Driver.api_key == api_key_header).first()
    if not driver:
        raise HTTPException(status_code=401, detail="Acesso negado. X-API-Key inválida.")
    return driver

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# === ROTAS PÚBLICAS ===
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "KMetrix API online e recebendo coordenadas."}

@app.post("/drivers/", response_model=schemas.DriverResponse, status_code=201, tags=["Setup"])
def create_driver(driver: schemas.DriverCreate, db: Session = Depends(get_db)):
    if db.query(models.Driver).filter(models.Driver.email == driver.email).first():
         raise HTTPException(status_code=400, detail="E-mail já registrado.")

    hashed_pwd = hashlib.sha256(driver.password.encode()).hexdigest()
    new_driver = models.Driver(
        name=driver.name, email=driver.email, hashed_password=hashed_pwd, api_key=secrets.token_hex(16)
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    return new_driver

@app.post("/auth/login", response_model=schemas.LoginResponse, tags=["Setup"])
def login_driver(credentials: schemas.DriverLogin, db: Session = Depends(get_db)):
    driver = db.query(models.Driver).filter(models.Driver.email == credentials.email).first()
    if not driver:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    hashed_pwd = hashlib.sha256(credentials.password.encode()).hexdigest()
    if driver.hashed_password != hashed_pwd:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    return {"api_key": driver.api_key}

# === PERFIL FINANCEIRO ===
@app.get("/financial-profile/", response_model=schemas.FinancialProfileResponse, tags=["Financeiro"])
def get_financial_profile(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    profile = db.query(models.FinancialProfile).filter(models.FinancialProfile.driver_id == current_driver.id).first()
    if not profile: raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    return profile

@app.put("/financial-profile/", response_model=schemas.FinancialProfileResponse, tags=["Financeiro"])
def update_financial_profile(profile_data: schemas.FinancialProfileCreate, current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    profile = db.query(models.FinancialProfile).filter(models.FinancialProfile.driver_id == current_driver.id).first()
    if profile:
        for key, value in profile_data.model_dump().items(): setattr(profile, key, value)
    else:
        profile = models.FinancialProfile(**profile_data.model_dump(), driver_id=current_driver.id)
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

# === GESTÃO DE TURNOS ===
@app.get("/shifts/current", response_model=schemas.ShiftResponse, tags=["Turnos"])
def get_current_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    # CORREÇÃO: Pega sempre o mais recente que não esteja encerrado
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status != "ENDED"
    ).order_by(models.Shift.created_at.desc()).first()
    
    if not shift: raise HTTPException(status_code=404, detail="Nenhum turno ativo.")
    return shift

@app.post("/shifts/start", response_model=schemas.ShiftResponse, status_code=201, tags=["Turnos"])
def start_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    # CORREÇÃO: Impede abertura se houver qualquer turno não encerrado
    existing_shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status != "ENDED"
    ).first()
    
    if existing_shift:
        raise HTTPException(status_code=400, detail="Turno já aberto.")
        
    new_shift = models.Shift(driver_id=current_driver.id, status="ACTIVE")
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    db.add(models.ShiftLog(shift_id=new_shift.id, event_type="START"))
    db.commit()
    return new_shift

@app.post("/shifts/pause", response_model=schemas.ShiftResponse, tags=["Turnos"])
def pause_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status == "ACTIVE"
    ).order_by(models.Shift.created_at.desc()).first()
    
    if not shift: raise HTTPException(status_code=400, detail="Nenhum turno ATIVO para pausar.")
    shift.status = "PAUSED"
    db.add(models.ShiftLog(shift_id=shift.id, event_type="PAUSE"))
    db.commit()
    db.refresh(shift)
    return shift

@app.post("/shifts/resume", response_model=schemas.ShiftResponse, tags=["Turnos"])
def resume_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status == "PAUSED"
    ).order_by(models.Shift.created_at.desc()).first()
    
    if not shift: raise HTTPException(status_code=400, detail="Nenhum turno PAUSADO para retomar.")
    shift.status = "ACTIVE"
    db.add(models.ShiftLog(shift_id=shift.id, event_type="RESUME"))
    db.commit()
    db.refresh(shift)
    return shift

@app.post("/shifts/end", response_model=schemas.ShiftResponse, tags=["Turnos"])
def end_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    # CORREÇÃO VITAL: Evita o .in_() e garante a seleção do turno exato
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status != "ENDED"
    ).order_by(models.Shift.created_at.desc()).first()
    
    if not shift: raise HTTPException(status_code=400, detail="Nenhum turno aberto para encerrar.")
    shift.status = "ENDED"
    shift.end_time = datetime.now(timezone.utc)
    db.add(models.ShiftLog(shift_id=shift.id, event_type="END"))
    db.commit()
    db.refresh(shift)
    return shift

# === INGESTÃO DE DADOS (GPS e Corridas Lidas) ===

@app.post("/shifts/gps", tags=["Ingestão de Dados"])
def register_gps_tick(gps_data: schemas.GpsTickCreate, current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status == "ACTIVE"
    ).order_by(models.Shift.created_at.desc()).first()
    
    if not shift: raise HTTPException(status_code=400, detail="Turno inativo. GPS ignorado.")

    last_log = db.query(models.ShiftLog).filter(
        models.ShiftLog.shift_id == shift.id,
        models.ShiftLog.event_type == "GPS_TICK",
        models.ShiftLog.latitude.isnot(None),
        models.ShiftLog.longitude.isnot(None)
    ).order_by(models.ShiftLog.timestamp.desc()).first()

    distance = 0.0
    if last_log:
        distance = calculate_distance(float(last_log.latitude), float(last_log.longitude), gps_data.latitude, gps_data.longitude)
        
        if distance < 5.0:  
            shift.total_km = float(shift.total_km) + distance
            if gps_data.is_paid_route:
                shift.paid_km = float(shift.paid_km) + distance
            else:
                shift.empty_km = float(shift.empty_km) + distance

    new_log = models.ShiftLog(
        shift_id=shift.id,
        event_type="GPS_TICK",
        latitude=gps_data.latitude,
        longitude=gps_data.longitude,
        is_paid_route=gps_data.is_paid_route
    )
    db.add(new_log)
    db.commit()

    return {"msg": "GPS registrado", "distance_added_km": round(distance, 3)}

@app.post("/rides/", response_model=schemas.RideResponse, status_code=201, tags=["Ingestão de Dados"])
def create_ride(ride: schemas.RideCreate, current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status != "ENDED"
    ).order_by(models.Shift.created_at.desc()).first()
    
    if not shift: raise HTTPException(status_code=400, detail="Nenhum turno aberto para atrelar a corrida.")

    new_ride = models.Ride(
        shift_id=shift.id,
        platform=ride.platform,
        status=ride.status,
        profit=ride.profit,
        distance_km=ride.distance_km,
        duration_minutes=ride.duration_minutes,
        alerts=ride.alerts
    )
    db.add(new_ride)
    db.commit()
    db.refresh(new_ride)
    return new_ride

# === RADAR E HISTÓRICO ===

@app.get("/shifts/current/radar", response_model=schemas.RadarResponse, tags=["Contabilidade"])
def get_earnings_radar(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status != "ENDED"
    ).order_by(models.Shift.created_at.desc()).first()
    
    if not shift: raise HTTPException(status_code=404, detail="Inicie um turno para ver o radar.")

    profile = db.query(models.FinancialProfile).filter(models.FinancialProfile.driver_id == current_driver.id).first()
    if not profile: raise HTTPException(status_code=400, detail="Configure o perfil financeiro primeiro.")

    monthly_costs = float(profile.rent_cost) + float(profile.insurance_cost) + float(profile.other_fixed_costs)
    daily_fixed_cost = monthly_costs / 30.0

    gross_profit = db.query(sa_func.sum(models.Ride.profit)).filter(
        models.Ride.shift_id == shift.id, models.Ride.status == "ACCEPTED"
    ).scalar() or 0.0

    current_net_balance = float(gross_profit) - daily_fixed_cost

    return {
        "shift_id": shift.id,
        "daily_fixed_cost": round(daily_fixed_cost, 2),
        "current_gross_profit": round(gross_profit, 2),
        "current_net_balance": round(current_net_balance, 2),
        "is_positive": current_net_balance >= 0
    }

@app.get("/rides/history", response_model=List[schemas.RideResponse], tags=["Histórico de Corridas"])
def get_ride_history(platform: Optional[str] = Query(None), status: Optional[str] = Query(None), current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shifts = db.query(models.Shift.id).filter(models.Shift.driver_id == current_driver.id).subquery()
    query = db.query(models.Ride).filter(models.Ride.shift_id.in_(shifts))
    
    if platform: query = query.filter(models.Ride.platform == platform)
    if status: query = query.filter(models.Ride.status == status)
        
    return query.order_by(models.Ride.timestamp.desc()).all()
