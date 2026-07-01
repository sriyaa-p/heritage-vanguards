# Local SSL Certificates for Nginx

To run this application securely over HTTPS in local development, you need to generate a self-signed SSL certificate and private key. 

To prevent security leaks, all `.crt`, `.key`, `.pem`, and `.txt` files in this directory are configured to be ignored by Git (except this `README.md`).

## Generating Development Certificates

Run the following command in this directory (`nginx/certs/`) to generate a certificate and private key valid for 365 days:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout localhost.key \
  -out localhost.crt \
  -subj "/CN=localhost"
```

Once generated, you should see two files in this directory:
- `localhost.crt` (the self-signed certificate)
- `localhost.key` (the private key)

When you run `docker compose up --build`, Docker will mount these certificates into the Nginx container, allowing you to access the app at `https://localhost`.
