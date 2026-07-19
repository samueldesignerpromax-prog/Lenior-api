FROM python:3.11-slim

WORKDIR /app

# Copia o requirements.txt primeiro (melhor para cache)
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY . .

# Expõe a porta que o Render usa
EXPOSE 10000

# Comando para rodar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
