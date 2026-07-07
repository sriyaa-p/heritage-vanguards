#!/bin/sh
# Auto-generates a self-signed SSL cert for localhost if one doesn't already exist.
# Called by the nginx Docker entrypoint before starting nginx.

CERT_DIR="/etc/nginx/certs"
CRT="$CERT_DIR/localhost.crt"
KEY="$CERT_DIR/localhost.key"

if [ ! -f "$CRT" ] || [ ! -f "$KEY" ]; then
  echo "==> [nginx] SSL certs not found. Generating self-signed certs..."
  mkdir -p "$CERT_DIR"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY" \
    -out "$CRT" \
    -subj "/C=US/ST=Local/L=Local/O=HeritageVanguards/CN=localhost"
  echo "==> [nginx] Self-signed certs generated at $CERT_DIR"
else
  echo "==> [nginx] SSL certs already exist. Skipping generation."
fi
