FROM python:3.11-slim

WORKDIR /app

# 1. Install system-level dependencies FIRST
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Set up virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 3. Upgrade pip and install core build tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir setuptools wheel

# 4. Copy requirements and install
# NOTE: Build context is backend/ so requirements.txt is at root of context
COPY requirements.txt .
RUN pip install --default-timeout=120 --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY . .

# 6. Copy scripts from repo root /scripts into container
COPY scripts/ /scripts/

# 7. Configure entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# 8. Healthcheck so Railway/Render knows when the backend is truly ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["/entrypoint.sh"]
