from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
import secrets
import hashlib # Apenas para um hash simples agora. No futuro, usaremos Passlib/Bcrypt.

# Importações locais do projeto
from database import engine, Base, get_db
import models
import schemas

# 1. Cria as tabelas no banco de dados
Base.metadata.create_all(bind=engine)

# 2. Inicializa o FastAPI
app = FastAPI(
    title="KMetrix API",
    description="Backend tático e financeiro para motoristas de app.",
    version="1.0.0"
)

# 3. Configuração de Segurança Multitenant (Cada motorista tem sua X-API-Key)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def get_current_driver(
    api_key_header: str = Security(api_key_header), 
    db: Session = Depends(get_db)
) -> models.Driver:
    """
    Middleware: Busca o motorista no banco de dados usando a chave da requisição.
    Garante isolamento total de dados para quando o app for comercializado.
    """
    driver = db.query(models.Driver).filter(models.Driver.api_key == api_key_header).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado. X-API-Key inválida ou inexistente.",
        )
    return driver


# ==========================================
# ROTAS PÚBLICAS 
# ==========================================

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "KMetrix API está online e pronta para escalar."}

@app.post("/drivers/", response_model=schemas.DriverResponse, status_code=status.HTTP_201_CREATED, tags=["Setup / Autenticação"])
def create_driver(driver: schemas.DriverCreate, db: Session = Depends(get_db)):
    """
    Cria um novo motorista. Se for comercializado, milhares de usuários baterão aqui.
    Retorna a X-API-Key que o app deverá salvar no armazenamento local do celular.
    """
    # Verifica se o email já está em uso
    existing_user = db.query(models.Driver).filter(models.Driver.email == driver.email).first()
    if existing_user:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está registrado.",
        )

    # Hash temporário simples para proteger a senha no banco na Fase 1
    hashed_pwd = hashlib.sha256(driver.password.encode()).hexdigest()
    
    # Gera uma chave de API segura e única para este motorista
    generated_api_key = secrets.token_hex(16)
    
    new_driver = models.Driver(
        name=driver.name,
        email=driver.email,
        hashed_password=hashed_pwd,
        api_key=generated_api_key
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    
    return new_driver


# ==========================================
# ROTAS PROTEGIDAS (Exigem X-API-Key no Header)
# ==========================================

@app.get("/me/", response_model=schemas.DriverResponse, tags=["Perfil do Motorista"])
def get_my_profile(current_driver: models.Driver = Depends(get_current_driver)):
    """
    Retorna os dados do motorista autenticado.
    Cada usuário verá APENAS os seus próprios dados, graças à X-API-Key.
    """
    return current_driver
