FROM python:3.9-slim

WORKDIR /app

COPY src/demo-environment/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/demo-environment/ .
COPY src/demo-environment/migrations/ ./migrations/

EXPOSE 8000

# Default CMD runs migrations then api_server
# Override in docker-compose for job_processor
CMD ["sh", "-c", "python run_migrations.py && python api_server.py"]
