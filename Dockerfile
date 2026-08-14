# Usa uma imagem oficial e leve do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de dependências primeiro (otimiza o tempo de build)
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código para dentro do contêiner
COPY . .

# Expõe a porta que o FastAPI vai rodar
EXPOSE 8000

# Comando para iniciar a API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
