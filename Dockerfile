FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e ".[dashboard]"

COPY dashboard/ dashboard/
COPY demo/ demo/

CMD ["dqtk", "--help"]
