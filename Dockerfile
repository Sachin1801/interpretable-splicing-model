# Multi-stage build for smaller image
FROM python:3.10-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies for Python wheels and ViennaRNA
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Build ViennaRNA from source
ARG VIENNARNA_VERSION=2.6.4
RUN wget -q https://www.tbi.univie.ac.at/RNA/download/sourcecode/2_6_x/ViennaRNA-${VIENNARNA_VERSION}.tar.gz \
    && tar -xzf ViennaRNA-${VIENNARNA_VERSION}.tar.gz \
    && cd ViennaRNA-${VIENNARNA_VERSION} \
    && ./configure --without-perl --without-python --without-doc --prefix=/opt/viennarna \
    && make -j$(nproc) \
    && make install \
    && cd .. \
    && rm -rf ViennaRNA-${VIENNARNA_VERSION} ViennaRNA-${VIENNARNA_VERSION}.tar.gz

# Install Python dependencies to a virtual env for cleaner copy
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production image
FROM python:3.10-slim-bookworm

WORKDIR /app

# Install runtime dependencies for matplotlib and ViennaRNA (libgomp for OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libxcb1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy ViennaRNA binaries from builder
COPY --from=builder /opt/viennarna /opt/viennarna
ENV PATH="/opt/viennarna/bin:${PATH}"

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY webapp/ ./webapp/
COPY figures/ ./figures/
COPY output/ ./output/
COPY data/ ./data/

# Create non-root user (HF Spaces requires user with uid 1000)
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

# Expose port (HF Spaces requires 7860)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:7860/api/health')" || exit 1

# Run with Uvicorn on port 7860 for HF Spaces
CMD ["python", "-m", "uvicorn", "webapp.app.main:app", "--host", "0.0.0.0", "--port", "7860"]
