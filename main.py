from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional

import models
from database import engine, get_db

# ==========================================
# CONFIGURAÇÕES DE AMBIENTE
# ==========================================
class Settings(BaseSettings):
    database_url: str
    domain_url: str
    encrypted_key: str

    class Config:
        env_file = ".env"

settings = Settings()

# Cria as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

# Inicializa a API
app = FastAPI(
    title="KMetrix API",
    description="Motor de cálculo de rentabilidade e rastreamento para motoristas.",
    version="1.0.0"
)

# ==========================================
# SCHEMAS (Validação de Dados de Entrada)
# ==========================================
class TurnoCreate(BaseModel):
    km_inicial: float

class TurnoEncerrar(BaseModel):
    km_final: float

class DespesaCreate(BaseModel):
    categoria: str
    valor: float

class CorridaCreate(BaseModel):
    plataforma: str
    status: str
    distancia_km: float
    tempo_minutos: int
    valor_bruto: float
    lucro_liquido: float

# ==========================================
# ROTAS DA API
# ==========================================

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "KMetrix API",
        "mensagem": "Servidor rodando perfeitamente!"
    }

# 1. INICIAR TURNO
@app.post("/turnos/iniciar")
def iniciar_turno(turno: TurnoCreate, db: Session = Depends(get_db)):
    # Verifica se já existe um turno ativo
    turno_ativo = db.query(models.Turno).filter(models.Turno.ativo == True).first()
    if turno_ativo:
        raise HTTPException(status_code=400, detail="Já existe um turno ativo.")

    novo_turno = models.Turno(
        km_inicial=turno.km_inicial,
        ativo=True,
        meta_diaria=-150.0 # Custo fixo do HR-V
    )
    db.add(novo_turno)
    db.commit()
    db.refresh(novo_turno)
    return {"mensagem": "Turno iniciado com sucesso!", "turno_id": novo_turno.id}

# 2. LANÇAR DESPESA
@app.post("/turnos/{turno_id}/despesas")
def lancar_despesa(turno_id: int, despesa: DespesaCreate, db: Session = Depends(get_db)):
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id, models.Turno.ativo == True).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno ativo não encontrado.")

    nova_despesa = models.Despesa(
        turno_id=turno.id,
        categoria=despesa.categoria,
        valor=despesa.valor
    )
    db.add(nova_despesa)
    
    # Atualiza a meta diária (aumenta o buraco que precisamos cobrir)
    turno.meta_diaria -= despesa.valor
    
    db.commit()
    return {"mensagem": f"Despesa de {despesa.categoria} registrada!", "nova_meta": turno.meta_diaria}

# 3. REGISTRAR CORRIDA
@app.post("/turnos/{turno_id}/corridas")
def registrar_corrida(turno_id: int, corrida: CorridaCreate, db: Session = Depends(get_db)):
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id, models.Turno.ativo == True).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno ativo não encontrado.")

    nova_corrida = models.Corrida(
        turno_id=turno.id,
        plataforma=corrida.plataforma,
        status=corrida.status,
        distancia_km=corrida.distancia_km,
        tempo_minutos=corrida.tempo_minutos,
        valor_bruto=corrida.valor_bruto,
        lucro_liquido=corrida.lucro_liquido
    )
    db.add(nova_corrida)

    # Se a corrida foi aceita, soma no KM Pago e abate na meta
    if corrida.status.lower() == "aceita":
        turno.km_pago += corrida.distancia_km
        turno.meta_diaria += corrida.lucro_liquido

    db.commit()
    return {"mensagem": "Corrida registrada com sucesso!", "saldo_do_dia": turno.meta_diaria}

# 4. ENCERRAR TURNO
@app.put("/turnos/{turno_id}/encerrar")
def encerrar_turno(turno_id: int, dados: TurnoEncerrar, db: Session = Depends(get_db)):
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id, models.Turno.ativo == True).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno ativo não encontrado.")

    turno.km_final = dados.km_final
    km_total_rodado = dados.km_final - turno.km_inicial
    turno.km_vazio = km_total_rodado - turno.km_pago
    
    turno.ativo = False
    turno.data_fim = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(turno)
    
    return {
        "mensagem": "Turno encerrado!",
        "resumo": {
            "km_total": km_total_rodado,
            "km_pago": turno.km_pago,
            "km_vazio": turno.km_vazio,
            "lucro_final": turno.meta_diaria
        }
    }
