from fastapi import FastAPI
from pydantic_settings import BaseSettings

# Configuração rigorosa das Variáveis de Ambiente
class Settings(BaseSettings):
    database_url: str
    domain_url: str
    encrypted_key: str

    class Config:
        env_file = ".env"

# Instancia as configurações
settings = Settings()

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
        "domain_configurado": settings.domain_url
    }
