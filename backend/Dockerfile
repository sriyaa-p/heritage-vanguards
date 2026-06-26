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

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
