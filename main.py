from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from datetime import datetime, timezone

import models
from database import engine, get_db

# ==========================================
# CONFIGURAÇÕES DE AMBIENTE E SEGURANÇA
# ==========================================
class Settings(BaseSettings):
    database_url: str
    domain_url: str
    encrypted_key: str

    class Config:
        env_file = ".env"

settings = Settings()

# Configuração da Chave de Segurança no Cabeçalho (Header)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def validar_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.encrypted_key:
        raise HTTPException(status_code=403, detail="Acesso negado. Chave inválida.")
    return api_key

# Cria as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

# Inicializa a API
app = FastAPI(
    title="KMetrix API",
    description="Motor de cálculo de rentabilidade e rastreamento para motoristas.",
    version="1.1.0"
)

# ==========================================
# SCHEMAS (Validação de Dados)
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
# ROTAS DA API (Agora protegidas pela API Key)
# ==========================================

@app.get("/")
def read_root():
    return {"status": "online", "app": "KMetrix API", "seguranca": "Ativa"}

# --- ROTAS DE ESCRITA (Que você já tinha) ---

@app.post("/turnos/iniciar", dependencies=[Depends(validar_api_key)])
def iniciar_turno(turno: TurnoCreate, db: Session = Depends(get_db)):
    turno_ativo = db.query(models.Turno).filter(models.Turno.ativo == True).first()
    if turno_ativo:
        raise HTTPException(status_code=400, detail="Já existe um turno ativo.")

    novo_turno = models.Turno(km_inicial=turno.km_inicial, ativo=True, meta_diaria=-150.0)
    db.add(novo_turno)
    db.commit()
    db.refresh(novo_turno)
    return {"mensagem": "Turno iniciado!", "turno_id": novo_turno.id}

@app.post("/turnos/{turno_id}/despesas", dependencies=[Depends(validar_api_key)])
def lancar_despesa(turno_id: int, despesa: DespesaCreate, db: Session = Depends(get_db)):
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id, models.Turno.ativo == True).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno não encontrado.")

    nova_despesa = models.Despesa(turno_id=turno.id, categoria=despesa.categoria, valor=despesa.valor)
    db.add(nova_despesa)
    turno.meta_diaria -= despesa.valor # Aumenta o buraco a ser coberto
    db.commit()
    return {"mensagem": "Despesa registrada!", "nova_meta": turno.meta_diaria}

@app.post("/turnos/{turno_id}/corridas", dependencies=[Depends(validar_api_key)])
def registrar_corrida(turno_id: int, corrida: CorridaCreate, db: Session = Depends(get_db)):
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id, models.Turno.ativo == True).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno não encontrado.")

    nova_corrida = models.Corrida(
        turno_id=turno.id, plataforma=corrida.plataforma, status=corrida.status,
        distancia_km=corrida.distancia_km, tempo_minutos=corrida.tempo_minutos,
        valor_bruto=corrida.valor_bruto, lucro_liquido=corrida.lucro_liquido
    )
    db.add(nova_corrida)

    if corrida.status.lower() == "aceita":
        turno.km_pago += corrida.distancia_km
        turno.meta_diaria += corrida.lucro_liquido # Abate do custo de R$ 150

    db.commit()
    return {"mensagem": "Corrida registrada!", "saldo_atual": turno.meta_diaria}

@app.put("/turnos/{turno_id}/encerrar", dependencies=[Depends(validar_api_key)])
def encerrar_turno(turno_id: int, dados: TurnoEncerrar, db: Session = Depends(get_db)):
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id, models.Turno.ativo == True).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno não encontrado.")

    turno.km_final = dados.km_final
    km_total = dados.km_final - turno.km_inicial
    turno.km_vazio = km_total - turno.km_pago
    turno.ativo = False
    turno.data_fim = datetime.now(timezone.utc)
    
    db.commit()
    return {"mensagem": "Turno encerrado!", "lucro_final": turno.meta_diaria}

# --- NOVAS ROTAS DE LEITURA (Para o App Mobile) ---

@app.get("/turnos/ativo", dependencies=[Depends(validar_api_key)])
def buscar_turno_ativo(db: Session = Depends(get_db)):
    """Verifica se existe um turno rodando ao abrir o app."""
    turno = db.query(models.Turno).filter(models.Turno.ativo == True).first()
    if not turno:
        return {"turno_ativo": False}
    return {"turno_ativo": True, "turno_id": turno.id, "saldo_atual": turno.meta_diaria}

@app.get("/turnos/{turno_id}/dashboard", dependencies=[Depends(validar_api_key)])
def obter_dados_dashboard(turno_id: int, db: Session = Depends(get_db)):
    """Fornece os dados mastigados para a tela estilo Power BI."""
    turno = db.query(models.Turno).filter(models.Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno não encontrado.")
    
    corridas_aceitas = db.query(models.Corrida).filter(
        models.Corrida.turno_id == turno_id, 
        models.Corrida.status == "Aceita"
    ).all()

    total_uber = sum(c.lucro_liquido for c in corridas_aceitas if c.plataforma == "Uber")
    total_99 = sum(c.lucro_liquido for c in corridas_aceitas if c.plataforma == "99")

    return {
        "velocimetro_saldo": turno.meta_diaria,
        "km_pago": turno.km_pago,
        "faturamento_plataformas": {"Uber": total_uber, "99": total_99},
        "total_corridas": len(corridas_aceitas)
    }

@app.get("/turnos/{turno_id}/historico", dependencies=[Depends(validar_api_key)])
def obter_historico(turno_id: int, db: Session = Depends(get_db)):
    """Retorna a lista completa para as abas de Histórico."""
    corridas = db.query(models.Corrida).filter(models.Corrida.turno_id == turno_id).order_by(models.Corrida.data_hora.desc()).all()
    return corridas
