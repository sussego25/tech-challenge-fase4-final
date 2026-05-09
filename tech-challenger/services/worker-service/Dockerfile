# Build context deve ser tech-challenger/ (para incluir shared/)
# Exemplo: docker build -f services/worker-service/Dockerfile .

# ---- deps stage ----
FROM python:3.11-slim AS deps

WORKDIR /build

COPY services/worker-service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage ----
FROM python:3.11-slim AS runtime

# Cria usuario nao-root
RUN useradd --create-home --no-log-init appuser

WORKDIR /app

# Copia dependencias instaladas
COPY --from=deps /install /usr/local

# Copia shared/ (contracts e libs)
COPY shared/contracts /app/shared/contracts
COPY shared/libs      /app/shared/libs

# Copia codigo do servico
COPY services/worker-service/src /app/src

# Torna shared/ disponivel para imports: libs.aws, libs.messaging, contracts.*
ENV PYTHONPATH="/app/src:/app/shared"

USER appuser

CMD ["python", "-m", "jobs.worker"]
