# VALGEOUGST — Hetzner VPS Deployment Guide

Step-by-step instructions for deploying VALGEOUGST to a **Hetzner CX32** VPS.

---

## Prerequisites

- **Hetzner CX32 VPS** (8 GB RAM, 4 vCPU, 80 GB disk, ~€8/mo)
- A domain name with an **A record** pointing to the VPS IP address
- SSH access to the VPS (root or sudo user)
- Git installed on your local machine

---

## Step 1: Initial VPS Setup

SSH into the VPS and harden it before deploying anything.

```bash
ssh root@YOUR_VPS_IP
```

### Update the system

```bash
apt update && apt upgrade -y
```

### Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose plugin
apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

### Create a non-root deploy user

```bash
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy

# Copy your SSH key to the new user
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
```

### Configure the firewall (ufw)

```bash
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
ufw status
```

---

## Step 2: Clone and Configure

Switch to the deploy user and set up the application.

```bash
su - deploy
```

### Clone the repository

```bash
git clone https://github.com/YOUR_ORG/UGST_OBJ1.git /home/deploy/valgeougst
cd /home/deploy/valgeougst
```

### Create the environment file

```bash
cp .env.example .env
```

### Generate a secure SECRET_KEY

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Copy the output and set it in `.env`:

```bash
nano .env
```

Fill in the required values:

```dotenv
FLASK_ENV=production

# Paste the generated key here — never reuse or share it
SECRET_KEY=<output-from-above>

# PostgreSQL connection string — must match POSTGRES_PASSWORD below
DATABASE_URL=postgresql://valgeougst:<STRONG_PASSWORD>@db:5432/valgeougst
POSTGRES_PASSWORD=<STRONG_PASSWORD>

# Your domain name (no trailing slash, no https://)
DOMAIN=yourdomain.example.com
```

> **Security note:** Never commit `.env` to version control. It is listed in `.gitignore`.

---

## Step 3: Deploy with Docker

### Build and start all services

```bash
docker compose up -d --build
```

### Wait for PostgreSQL to be ready

```bash
# Watch the db container logs until you see "database system is ready to accept connections"
docker compose logs -f db
# Press Ctrl+C once ready
```

### Initialize the database schema

```bash
docker compose exec web python scripts/init_db.py
```

### Create the admin user

```bash
docker compose exec web python scripts/create_admin.py \
  --username admin \
  --email admin@example.com \
  --password CHANGE_ME
```

> **Important:** Change the admin password immediately after first login.

---

## Step 4: SSL Certificate (Let's Encrypt)

### Run the initialization script

```bash
chmod +x scripts/init-letsencrypt.sh
./scripts/init-letsencrypt.sh yourdomain.example.com
```

This script:
1. Obtains a certificate from Let's Encrypt via the webroot challenge
2. Replaces the `DOMAIN` placeholder in `nginx/nginx.conf`
3. Reloads Nginx

### Switch Nginx to the SSL config

```bash
# The init script handles this, but if you need to do it manually:
cp nginx/nginx.conf nginx/nginx-active.conf
docker compose restart nginx
```

### Verify HTTPS is working

```bash
curl -I https://yourdomain.example.com
# Expect: HTTP/2 200
```

---

## Step 5: Verify the Deployment

1. Open **https://yourdomain.example.com** in a browser
2. Log in with the admin credentials created in Step 3
3. Upload a test Excel file and confirm the data imports correctly
4. Open a polygon record and verify the map loads correctly
5. Generate a test PDF ficha técnica and download it

If all five checks pass, the deployment is complete.

---

## Maintenance

### View application logs

```bash
docker compose logs -f web
```

### Backup the database

```bash
docker compose exec db pg_dump -U valgeougst valgeougst > backup_$(date +%Y%m%d_%H%M%S).sql
```

Store backups off-server (e.g., Hetzner Object Storage or a local machine).

### Restore from backup

```bash
docker compose exec -T db psql -U valgeougst valgeougst < backup_YYYYMMDD_HHMMSS.sql
```

### Update the application

```bash
git pull
docker compose up -d --build
```

### Monitor RAM usage

```bash
free -h
```

RAM should stay **under 6 GB** during normal operation on the CX32:

| Component | Approx. RAM |
|---|---|
| OS + system processes | ~0.5 GB |
| PostgreSQL | ~0.3 GB |
| Nginx | ~0.1 GB |
| Gunicorn master (shapefiles preloaded) | ~1.2 GB |
| Gunicorn worker × 2 (copy-on-write) | ~0.4 GB |
| **Total** | **~2.5 GB** |

> **Warning:** Do **not** run more than **2 Gunicorn workers** on the CX32. Each worker loads ~1.2 GB of shapefiles into RAM. With `preload_app = True` the master process shares memory via copy-on-write, but adding a third worker still risks OOM on an 8 GB VPS. See `gunicorn.conf.py` for details.

---

## Troubleshooting

### App won't start

```bash
docker compose logs web
```

Common causes:
- `SECRET_KEY` not set in `.env`
- `DATABASE_URL` wrong or PostgreSQL not yet ready
- Port 8000 already in use inside the container

### Maps load slowly or time out

```bash
free -h   # Check available RAM
docker compose logs web | grep worker
```

If RAM is tight, reduce Gunicorn workers to **1** in `gunicorn.conf.py`:

```python
workers = 1  # Temporary — upgrade VPS RAM for a permanent fix
```

Then restart:

```bash
docker compose restart web
```

### SSL certificate issues

```bash
docker compose logs nginx
# Check certbot renewal logs
docker compose exec nginx cat /var/log/letsencrypt/letsencrypt.log
```

Common causes:
- Domain DNS not yet propagated (wait up to 48 h after changing A record)
- Port 80 blocked by firewall (certbot needs it for the ACME challenge)
- Certificate already expired — run `./scripts/init-letsencrypt.sh yourdomain.example.com` again

### Database connection refused

```bash
docker compose ps       # Confirm db container is running
docker compose logs db  # Look for startup errors
```

Ensure `POSTGRES_PASSWORD` in `.env` matches the password in `DATABASE_URL`.
