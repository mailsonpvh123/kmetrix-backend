from fastapi import FastAPI
from pydantic_settings import BaseSettings
import models
from database import engine

# Configuração rigorosa das Variáveis de Ambiente
class Settings(BaseSettings):
    database_url: str
    domain_url: str
    encrypted_key: str

    class Config:
        env_file = ".env"

settings = Settings()

# Cria as tabelas no banco de dados automaticamente se não existirem
models.Base.metadata.create_all(bind=engine)

# Inicializa a API do KMetrix
app = FastAPI(
    title="KMetrix API",
    description="Motor de cálculo de rentabilidade e rastreamento para motoristas.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "KMetrix API",
        "domain_configurado": settings.domain_url,
        "mensagem": "Banco de dados conectado e tabelas criadas com sucesso!"
    }
