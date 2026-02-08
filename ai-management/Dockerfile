FROM python:3.9-slim

WORKDIR /app

COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files from models (production code)
COPY src/models/ /app/

EXPOSE 8001

CMD ["python", "ai_server.py"]