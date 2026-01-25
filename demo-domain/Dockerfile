FROM python:3.9-slim

WORKDIR /app

COPY src/demo-environment/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/demo-environment/ .

EXPOSE 8000

CMD ["python", "api_server.py"]
