# docker/app/Dockerfile

# Stage 1: Builder — install dependencies
FROM python:3.12-slim AS builder
WORKDIR /build

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Runtime — lean production image
FROM python:3.12-slim AS runtime
WORKDIR /app

# Non-root user for security
RUN addgroup --system agent && \
    adduser --system --ingroup agent agent

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

USER agent

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
