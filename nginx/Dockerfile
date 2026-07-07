FROM nginx:alpine

# Install openssl so we can generate self-signed certs at runtime
RUN apk add --no-cache openssl

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy cert generation script
COPY generate-certs.sh /docker-entrypoint.d/10-generate-certs.sh
RUN chmod +x /docker-entrypoint.d/10-generate-certs.sh

# nginx:alpine's entrypoint automatically runs all scripts in /docker-entrypoint.d/
# before starting nginx, so certs will always exist before nginx reads nginx.conf
