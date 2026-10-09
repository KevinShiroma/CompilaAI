FROM python:3.11-slim

# Garante saída de logs imediata no console
ENV PYTHONUNBUFFERED=1

# Instala ferramentas do sistema para áudio e certificados
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY bot.py .
COPY utils/ utils/
COPY data/ data/

# Cria diretório para arquivos temporários
RUN mkdir -p temp_media

# Inicia o bot
CMD ["python", "bot.py"]
