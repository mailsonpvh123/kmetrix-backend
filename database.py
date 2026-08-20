import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Captura a URL crua do EasyPanel
raw_url = os.getenv("DATABASE_URL")

# Correção Crítica e Robusta: 
# Garante que a conversão de 'postgres' para 'postgresql' ocorra ANTES de definir a variável final
if raw_url and raw_url.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = raw_url.replace("postgres://", "postgresql://", 1)
elif raw_url:
    SQLALCHEMY_DATABASE_URL = raw_url
else:
    # Fallback para caso rode localmente fora do EasyPanel
    SQLALCHEMY_DATABASE_URL = "sqlite:///./kmetrix_dev.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
