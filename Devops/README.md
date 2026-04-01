# Devops configs

This folder contains production deployment configs.

## Available stacks

- `docker-compose.prod.yml` + `Caddyfile`: HTTPS via Caddy (simple auto TLS).
- `docker-compose.nginx.prod.yml` + `nginx/`: HTTPS via Nginx + Certbot + rate limit.

## Nginx stack files

- `docker-compose.nginx.prod.yml`
- `nginx/nginx.bootstrap.conf.template`: HTTP-only config for first certificate issue.
- `nginx/nginx.conf.template`: HTTPS config with rate limit.

## Nginx required env

- `DOMAIN`: public domain that points to your VPS IP (example: `api.example.com`)
- `LETSENCRYPT_EMAIL`: email for Let's Encrypt registration
- `DATABASE_URL`: backend database URL
- `BACKEND_IMAGE`: backend image tag

## Nginx optional env

- `RATE_LIMIT_RPS` (default: `20`)
- `RATE_LIMIT_BURST` (default: `40`)
- `NGINX_CONF_TEMPLATE` (default: `./nginx/nginx.bootstrap.conf.template`)

## Nginx quick start on VPS

1. Prepare env values:

```bash
export DOMAIN=api.example.com
export LETSENCRYPT_EMAIL=ops@example.com
export DATABASE_URL='postgresql://user:password@host:5432/db?sslmode=require'
export BACKEND_IMAGE='your-user/roadsentinel-backend:v1.0.0'
export RATE_LIMIT_RPS=20
export RATE_LIMIT_BURST=40
```

2. Start bootstrap mode (HTTP only + ACME challenge):

```bash
docker compose -f docker-compose.nginx.prod.yml up -d backend nginx
```

3. Issue first certificate:

```bash
docker compose -f docker-compose.nginx.prod.yml --profile init run --rm certbot-init
```

4. Switch to HTTPS config and restart nginx:

```bash
export NGINX_CONF_TEMPLATE=./nginx/nginx.conf.template
docker compose -f docker-compose.nginx.prod.yml up -d nginx certbot-renew
```

## Notes

- Open inbound ports `80` and `443`.
- DNS for `DOMAIN` must resolve to VPS public IP before cert issuing.
- `certbot-renew` renews certs every 12h check interval; reload nginx after renewal when needed.
