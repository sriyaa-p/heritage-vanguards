FROM python:3.11-slim

WORKDIR /app

# 1. Install system-level dependencies FIRST
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 2. Set up virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 3. Upgrade pip and install core build tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir setuptools wheel

# 4. Copy requirements and install them
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# 5. Copy application code and scripts
COPY backend/ .
COPY scripts/ /scripts/

# 6. Configure entrypoint
COPY backend/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
