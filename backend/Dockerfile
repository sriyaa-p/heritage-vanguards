FROM python:3.11-slim

WORKDIR /app

# Set up virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Upgrade pip and install requirements with increased timeout
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --default-timeout=100 --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy scripts (fetch_unesco_data.py, seed_database.py) into the container
COPY scripts/ /scripts/

# Copy and configure the startup entrypoint script
COPY backend/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# On startup: create tables → seed UNESCO data → launch uvicorn
CMD ["/entrypoint.sh"]

