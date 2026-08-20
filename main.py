from fastapi import FastAPI, Depends, HTTPException, Security, status, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from datetime import datetime, timezone
from typing import Optional, List
import secrets
import hashlib 

from database import engine, Base, get_db
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="KMetrix API", version="1.1.0")

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

# === ROTAS PÚBLICAS ===
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "KMetrix API online."}

@app.post("/drivers/", response_model=schemas.DriverResponse, status_code=201, tags=["Setup"])
def create_driver(driver: schemas.DriverCreate, db: Session = Depends(get_db)):
    if db.query(models.Driver).filter(models.Driver.email == driver.email).first():
         raise HTTPException(status_code=400, detail="E-mail já registrado.")

    hashed_pwd = hashlib.sha256(driver.password.encode()).hexdigest()
    new_driver = models.Driver(
        name=driver.name,
        email=driver.email,
        hashed_password=hashed_pwd,
        api_key=secrets.token_hex(16)
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    return new_driver

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
    shift = db.query(models.Shift).filter(models.Shift.driver_id == current_driver.id, models.Shift.status.in_(["ACTIVE", "PAUSED"])).first()
    if not shift: raise HTTPException(status_code=404, detail="Nenhum turno ativo.")
    return shift

@app.post("/shifts/start", response_model=schemas.ShiftResponse, status_code=201, tags=["Turnos"])
def start_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    if db.query(models.Shift).filter(models.Shift.driver_id == current_driver.id, models.Shift.status.in_(["ACTIVE", "PAUSED"])).first():
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
    shift = db.query(models.Shift).filter(models.Shift.driver_id == current_driver.id, models.Shift.status == "ACTIVE").first()
    if not shift: raise HTTPException(status_code=400, detail="Nenhum turno ATIVO para pausar.")
    shift.status = "PAUSED"
    db.add(models.ShiftLog(shift_id=shift.id, event_type="PAUSE"))
    db.commit()
    db.refresh(shift)
    return shift

@app.post("/shifts/resume", response_model=schemas.ShiftResponse, tags=["Turnos"])
def resume_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(models.Shift.driver_id == current_driver.id, models.Shift.status == "PAUSED").first()
    if not shift: raise HTTPException(status_code=400, detail="Nenhum turno PAUSADO para retomar.")
    shift.status = "ACTIVE"
    db.add(models.ShiftLog(shift_id=shift.id, event_type="RESUME"))
    db.commit()
    db.refresh(shift)
    return shift

@app.post("/shifts/end", response_model=schemas.ShiftResponse, tags=["Turnos"])
def end_shift(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(models.Shift.driver_id == current_driver.id, models.Shift.status.in_(["ACTIVE", "PAUSED"])).first()
    if not shift: raise HTTPException(status_code=400, detail="Nenhum turno aberto para encerrar.")
    shift.status = "ENDED"
    shift.end_time = datetime.now(timezone.utc)
    db.add(models.ShiftLog(shift_id=shift.id, event_type="END"))
    db.commit()
    db.refresh(shift)
    return shift

# === RADAR DE GANHOS E HISTÓRICO (NOVAS ROTAS) ===

@app.get("/shifts/current/radar", response_model=schemas.RadarResponse, tags=["Contabilidade"])
def get_earnings_radar(current_driver: models.Driver = Depends(get_current_driver), db: Session = Depends(get_db)):
    """
    Calcula o Radar de Ganhos: 
    Pega os custos fixos, divide por 30 para achar a diária (fictícia), e abate do lucro ganho nas corridas ACEITAS hoje.
    """
    shift = db.query(models.Shift).filter(
        models.Shift.driver_id == current_driver.id, 
        models.Shift.status.in_(["ACTIVE", "PAUSED"])
    ).first()
    
    if not shift: raise HTTPException(status_code=404, detail="Inicie um turno para ver o radar.")

    profile = db.query(models.FinancialProfile).filter(models.FinancialProfile.driver_id == current_driver.id).first()
    if not profile: raise HTTPException(status_code=400, detail="Configure o perfil financeiro primeiro.")

    # 1. Calcula custo diário (Aluguel + Seguro + Outros fixos / 30)
    monthly_costs = float(profile.rent_cost) + float(profile.insurance_cost) + float(profile.other_fixed_costs)
    daily_fixed_cost = monthly_costs / 30.0

    # 2. Soma apenas o lucro das corridas com status "ACCEPTED" neste turno
    gross_profit = db.query(sa_func.sum(models.Ride.profit)).filter(
        models.Ride.shift_id == shift.id,
        models.Ride.status == "ACCEPTED"
    ).scalar() or 0.0

    # 3. Matemática do Radar
    current_net_balance = float(gross_profit) - daily_fixed_cost

    return {
        "shift_id": shift.id,
        "daily_fixed_cost": round(daily_fixed_cost, 2),
        "current_gross_profit": round(gross_profit, 2),
        "current_net_balance": round(current_net_balance, 2),
        "is_positive": current_net_balance >= 0
    }

@app.get("/rides/history", response_model=List[schemas.RideResponse], tags=["Histórico de Corridas"])
def get_ride_history(
    platform: Optional[str] = Query(None, description="Filtrar por app: Uber, 99, inDrive"),
    status: Optional[str] = Query(None, description="Filtrar por status: ACCEPTED, REJECTED, CANCELED"),
    current_driver: models.Driver = Depends(get_current_driver), 
    db: Session = Depends(get_db)
):
    """
    Retorna o histórico de corridas. 
    Permite filtrar por plataforma e apenas pelas corridas aceitas.
    """
    # Buscamos todos os turnos deste motorista primeiro
    shifts = db.query(models.Shift.id).filter(models.Shift.driver_id == current_driver.id).subquery()
    
    # Construímos a query base olhando apenas para corridas dos turnos do motorista
    query = db.query(models.Ride).filter(models.Ride.shift_id.in_(shifts))
    
    # Aplica os filtros se eles foram enviados na requisição
    if platform:
        query = query.filter(models.Ride.platform == platform)
    if status:
        query = query.filter(models.Ride.status == status)
        
    return query.order_by(models.Ride.timestamp.desc()).all()
