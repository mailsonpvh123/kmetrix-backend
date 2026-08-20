from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
import secrets
import hashlib 

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

# 3. Configuração de Segurança Multitenant
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def get_current_driver(
    api_key_header: str = Security(api_key_header), 
    db: Session = Depends(get_db)
) -> models.Driver:
    """
    Middleware: Busca o motorista no banco de dados usando a chave da requisição.
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
    Cria um novo motorista. Retorna a X-API-Key para o app.
    """
    existing_user = db.query(models.Driver).filter(models.Driver.email == driver.email).first()
    if existing_user:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está registrado.",
        )

    hashed_pwd = hashlib.sha256(driver.password.encode()).hexdigest()
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
# ROTAS PROTEGIDAS (Exigem X-API-Key)
# ==========================================

@app.get("/me/", response_model=schemas.DriverResponse, tags=["Perfil do Motorista"])
def get_my_profile(current_driver: models.Driver = Depends(get_current_driver)):
    """
    Retorna os dados do motorista autenticado.
    """
    return current_driver

# ------------------------------------------
# GESTÃO FINANCEIRA
# ------------------------------------------

@app.get("/financial-profile/", response_model=schemas.FinancialProfileResponse, tags=["Perfil Financeiro"])
def get_financial_profile(
    current_driver: models.Driver = Depends(get_current_driver), 
    db: Session = Depends(get_db)
):
    """
    Consulta os custos e metas (Entrevista de Custos) cadastrados do motorista logado.
    """
    profile = db.query(models.FinancialProfile).filter(models.FinancialProfile.driver_id == current_driver.id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil financeiro não encontrado. Envie os dados para criar um."
        )
        
    return profile

@app.put("/financial-profile/", response_model=schemas.FinancialProfileResponse, tags=["Perfil Financeiro"])
def update_financial_profile(
    profile_data: schemas.FinancialProfileCreate,
    current_driver: models.Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """
    Cria ou atualiza (UPSERT) a entrevista de custos do motorista logado.
    Garante que só exista um perfil ativo por motorista.
    """
    profile = db.query(models.FinancialProfile).filter(models.FinancialProfile.driver_id == current_driver.id).first()
    
    if profile:
        # Se já existe, atualiza os campos com os novos valores enviados pelo app
        for key, value in profile_data.model_dump().items():
            setattr(profile, key, value)
    else:
        # Se não existe, cria um novo vinculando ao ID do motorista
        profile = models.FinancialProfile(
            **profile_data.model_dump(),
            driver_id=current_driver.id
        )
        db.add(profile)
        
    db.commit()
    db.refresh(profile)
    
    return profile
