FROM python:3.12-slim

# The mysql client runs the .sql build scripts (they use DELIMITER blocks,
# which only the client understands).
RUN apt-get update \
 && apt-get install -y --no-install-recommends default-mysql-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV FLASK_DEBUG=0 PYTHONUNBUFFERED=1
EXPOSE 5000
ENTRYPOINT ["bash", "scripts/docker-entrypoint.sh"]
