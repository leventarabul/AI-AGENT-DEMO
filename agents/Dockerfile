FROM python:3.11-slim

WORKDIR /app

# Git gerekli (code review diff için)
RUN apt-get update \
	&& apt-get install -y --no-install-recommends git \
	&& rm -rf /var/lib/apt/lists/*

# Önce requirements.txt'i kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kaynak kodları kopyala
COPY . .

# Port ayarla
EXPOSE 8002

# Servisi başlat (--log-level debug için detaylı log)
CMD ["uvicorn", "ai_server:app", "--host", "0.0.0.0", "--port", "8002", "--log-level", "debug"]
