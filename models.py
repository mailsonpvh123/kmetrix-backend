import uuid
from sqlalchemy import Column, String, Numeric, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    
    # Preparação para o futuro comercial (Login por email/senha)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True) 
    
    # Autenticação Fase 1 (API Key única por usuário)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    financial_profile = relationship("FinancialProfile", back_populates="driver", uselist=False, cascade="all, delete")
    shifts = relationship("Shift", back_populates="driver", cascade="all, delete")


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), unique=True)
    
    rent_cost = Column(Numeric(10, 2), default=0.00)
    insurance_cost = Column(Numeric(10, 2), default=0.00)
    other_fixed_costs = Column(Numeric(10, 2), default=0.00)
    fuel_cost_per_liter = Column(Numeric(10, 2), default=0.00)
    vehicle_consumption = Column(Numeric(10, 2), default=0.00)
    target_per_km = Column(Numeric(10, 2), default=0.00)
    target_per_hour = Column(Numeric(10, 2), default=0.00)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    driver = relationship("Driver", back_populates="financial_profile")


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"))
    status = Column(String(20), nullable=False, default="ACTIVE")
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    total_km = Column(Numeric(10, 2), default=0.00)
    paid_km = Column(Numeric(10, 2), default=0.00)
    empty_km = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    driver = relationship("Driver", back_populates="shifts")
    logs = relationship("ShiftLog", back_populates="shift", cascade="all, delete")
    rides = relationship("Ride", back_populates="shift", cascade="all, delete")


class ShiftLog(Base):
    __tablename__ = "shift_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"))
    event_type = Column(String(50), nullable=False)
    
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    is_paid_route = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    shift = relationship("Shift", back_populates="logs")


class Ride(Base):
    __tablename__ = "rides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"))
    platform = Column(String(50), nullable=False)
    
    profit = Column(Numeric(10, 2), nullable=False)
    distance_km = Column(Numeric(10, 2), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    alerts = Column(JSONB, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    shift = relationship("Shift", back_populates="rides")
