from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# --- SCHEMAS PARA O PERFIL FINANCEIRO ---
class FinancialProfileBase(BaseModel):
    rent_cost: float = Field(default=0.0, ge=0.0, description="Custo do aluguel")
    insurance_cost: float = Field(default=0.0, ge=0.0, description="Custo do seguro")
    other_fixed_costs: float = Field(default=0.0, ge=0.0, description="Outros custos fixos")
    fuel_cost_per_liter: float = Field(default=0.0, ge=0.0, description="Preço do combustível")
    vehicle_consumption: float = Field(default=0.0, ge=0.0, description="Consumo do veículo (km/l)")
    target_per_km: float = Field(default=0.0, ge=0.0, description="Meta de ganho por KM")
    target_per_hour: float = Field(default=0.0, ge=0.0, description="Meta de ganho por Hora")

class FinancialProfileCreate(FinancialProfileBase):
    pass

class FinancialProfileResponse(FinancialProfileBase):
    id: UUID
    driver_id: UUID
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- SCHEMAS PARA O MOTORISTA ---
class DriverCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., description="E-mail de login para uso comercial no futuro")
    password: str = Field(..., min_length=6, description="Senha do usuário")

class DriverResponse(BaseModel):
    id: UUID
    name: str
    email: str
    api_key: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- SCHEMAS PARA O TURNO (SHIFT) ---
class ShiftCreate(BaseModel):
    pass 

class ShiftResponse(BaseModel):
    id: UUID
    driver_id: UUID
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_km: float
    paid_km: float
    empty_km: float
    
    model_config = ConfigDict(from_attributes=True)

# --- SCHEMAS PARA LOGS E GPS ---
class ShiftLogCreate(BaseModel):
    event_type: str = Field(..., description="START, PAUSE, RESUME, GPS_TICK, END")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_paid_route: bool = False

# --- SCHEMAS PARA CORRIDAS ---
class RideCreate(BaseModel):
    platform: str = Field(..., description="Uber, 99, inDrive")
    profit: float = Field(..., description="Valor líquido da corrida extraído da tela")
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    alerts: Optional[Dict[str, Any]] = None 

class RideResponse(RideCreate):
    id: UUID
    shift_id: UUID
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)
