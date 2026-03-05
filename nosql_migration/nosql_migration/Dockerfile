FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Les variables de connexion sont injectées via env_file dans docker-compose.yml
CMD ["python", "migrate_pg_to_neo4j_pg8000.py", "--truncate-neo4j"]
