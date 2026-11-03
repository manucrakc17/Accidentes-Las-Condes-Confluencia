FROM python:3.12-slim

LABEL maintainer="Equipo Siniestros Las Condes - Confluencia Científica"
LABEL description="Contenedor reproducible para desarrollo, experimentación estadística/espacial y auditoría de siniestros viales en Las Condes (2025)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    TZ=America/Santiago

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD ["python", "desarrollo/run_all.py"]
