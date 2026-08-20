from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class FinancialProfileBase(BaseModel):
    rent_cost: float = Field(default=0.0, ge=0.0)
    insurance_cost: float = Field(default=0.0, ge=0.0)
    other_fixed_costs: float = Field(default=0.0, ge=0.0)
    fuel_cost_per_liter: float = Field(default=0.0, ge=0.0)
    vehicle_consumption: float = Field(default=0.0, ge=0.0)
    target_per_km: float = Field(default=0.0, ge=0.0)
    target_per_hour: float = Field(default=0.0, ge=0.0)

class FinancialProfileCreate(FinancialProfileBase):
    pass

class FinancialProfileResponse(FinancialProfileBase):
    id: UUID
    driver_id: UUID
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DriverCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=6)

class DriverResponse(BaseModel):
    id: UUID
    name: str
    email: str
    api_key: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

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

class ShiftLogCreate(BaseModel):
    event_type: str = Field(...)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_paid_route: bool = False

class RideCreate(BaseModel):
    platform: str = Field(..., description="Uber, 99, inDrive")
    status: str = Field(default="ACCEPTED", description="ACCEPTED, REJECTED, CANCELED")
    profit: float = Field(..., description="Valor da corrida")
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    alerts: Optional[Dict[str, Any]] = None 

class RideResponse(RideCreate):
    id: UUID
    shift_id: UUID
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

# NOVO: Resposta mastigada para a tela do Radar de Ganhos
class RadarResponse(BaseModel):
    shift_id: UUID
    daily_fixed_cost: float
    current_gross_profit: float
    current_net_balance: float
    is_positive: bool
