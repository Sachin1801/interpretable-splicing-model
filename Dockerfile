# Multi-stage build for smaller image
FROM python:3.10-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY webapp/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production image
FROM python:3.10-slim-bookworm

WORKDIR /app

# Install system dependencies including ViennaRNA
RUN apt-get update && apt-get install -y --no-install-recommends \
    vienna-rna \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY webapp/ ./webapp/
COPY figures/ ./figures/
COPY output/ ./output/
COPY data/ ./data/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health')" || exit 1

# Run with Uvicorn
CMD ["python", "-m", "uvicorn", "webapp.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
