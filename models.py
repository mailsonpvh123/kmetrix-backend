from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    ativo = Column(Boolean, default=True)
    meta_diaria = Column(Float, default=-150.0) # O custo fixo do aluguel do HR-V
    km_inicial = Column(Float, nullable=True)
    km_final = Column(Float, nullable=True)
    km_vazio = Column(Float, default=0.0)
    km_pago = Column(Float, default=0.0)
    data_inicio = Column(DateTime(timezone=True), server_default=func.now())
    data_fim = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    corridas = relationship("Corrida", back_populates="turno")
    despesas = relationship("Despesa", back_populates="turno")

class Despesa(Base):
    __tablename__ = "despesas"

    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"))
    categoria = Column(String, index=True) # Ex: Combustível, Alimentação, Banheiro
    valor = Column(Float, nullable=False)
    data_hora = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamento
    turno = relationship("Turno", back_populates="despesas")

class Corrida(Base):
    __tablename__ = "corridas"

    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"))
    plataforma = Column(String, index=True) # Uber ou 99
    status = Column(String, index=True) # Recebida, Aceita, Ignorada
    distancia_km = Column(Float, nullable=False)
    tempo_minutos = Column(Integer, nullable=False)
    valor_bruto = Column(Float, nullable=False)
    lucro_liquido = Column(Float, nullable=False) # Valor bruto - custo do combustível do HR-V
    data_hora = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamento
    turno = relationship("Turno", back_populates="corridas")
