# Usa a imagem oficial e mais leve do Python 3.11
FROM python:3.11-slim

# Impede o Python de gravar arquivos .pyc no disco (otimiza espaço)
ENV PYTHONDONTWRITEBYTECODE=1
# Garante que os logs do FastAPI saiam no console do EasyPanel em tempo real
ENV PYTHONUNBUFFERED=1

# Define a pasta raiz dentro do contêiner
WORKDIR /app

# Instala dependências do sistema operacional necessárias para o PostgreSQL e pacotes matemáticos
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos primeiro para otimizar o cache do Docker
COPY requirements.txt .

# Instala as bibliotecas do back-end
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos do repositório para dentro do contêiner
COPY . .

# Expõe a porta padrão que o FastAPI vai utilizar
EXPOSE 8000

# O comando mestre que o EasyPanel vai rodar para ligar a API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
