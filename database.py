import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (quando rodar localmente)
load_dotenv()

# Pega a URL do banco de dados (O EasyPanel injetará isso automaticamente se configurado lá)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Cria o motor de conexão
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Cria a fábrica de sessões para o banco de dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base para criar os modelos (tabelas)
Base = declarative_base()

# Dependência para injetar o banco nas rotas da API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
