#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Automated first-deploy script for VALGEOUGST on Hetzner CX32
#
# Usage:
#   chmod +x scripts/deploy.sh
#   sudo ./scripts/deploy.sh
#
# This script is IDEMPOTENT — safe to run more than once.
# It will skip steps that are already complete (Docker installed, repo cloned,
# containers already running, etc.).
#
# What it does:
#   1. Installs Docker + Docker Compose plugin (if not present)
#   2. Creates a non-root 'deploy' user (if not present)
#   3. Clones the repository (if not already cloned)
#   4. Copies .env.example → .env (if .env does not exist)
#   5. Builds and starts all Docker services
#   6. Waits for PostgreSQL to be ready
#   7. Initialises the database schema
#
# After running this script you still need to:
#   - Edit /home/deploy/valgeougst/.env with real values (SECRET_KEY, passwords, DOMAIN)
#   - Create the admin user:
#       docker compose exec web python scripts/create_admin.py \
#         --username admin --email admin@example.com --password CHANGE_ME
#   - Obtain an SSL certificate:
#       ./scripts/init-letsencrypt.sh yourdomain.example.com
# =============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
REPO_URL="${REPO_URL:-https://github.com/YOUR_ORG/UGST_OBJ1.git}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/deploy/valgeougst}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
PG_READY_TIMEOUT=60   # seconds to wait for PostgreSQL

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Colour

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Require root ──────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  die "This script must be run as root (or with sudo)."
fi

# ── Step 1: Install Docker ────────────────────────────────────────────────────
info "Step 1: Checking Docker installation..."

if command -v docker &>/dev/null; then
  info "Docker already installed: $(docker --version)"
else
  info "Installing Docker..."
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg lsb-release

  # Add Docker's official GPG key and repository
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

  systemctl enable --now docker
  info "Docker installed: $(docker --version)"
fi

if ! docker compose version &>/dev/null; then
  die "Docker Compose plugin not found. Install docker-compose-plugin and retry."
fi
info "Docker Compose: $(docker compose version)"

# ── Step 2: Create deploy user ────────────────────────────────────────────────
info "Step 2: Ensuring deploy user '${DEPLOY_USER}' exists..."

if id "${DEPLOY_USER}" &>/dev/null; then
  info "User '${DEPLOY_USER}' already exists."
else
  adduser --disabled-password --gecos "" "${DEPLOY_USER}"
  info "User '${DEPLOY_USER}' created."
fi

# Ensure the user is in the docker group (idempotent)
usermod -aG docker "${DEPLOY_USER}"
info "User '${DEPLOY_USER}' added to docker group."

# ── Step 3: Clone repository ──────────────────────────────────────────────────
info "Step 3: Cloning repository..."

if [[ -d "${DEPLOY_DIR}/.git" ]]; then
  info "Repository already cloned at ${DEPLOY_DIR}. Pulling latest changes..."
  sudo -u "${DEPLOY_USER}" git -C "${DEPLOY_DIR}" pull --ff-only || \
    warn "git pull failed (local changes?). Continuing with existing code."
else
  if [[ "${REPO_URL}" == *"YOUR_ORG"* ]]; then
    die "REPO_URL is not set. Export it before running: export REPO_URL=https://github.com/your-org/repo.git"
  fi
  sudo -u "${DEPLOY_USER}" git clone "${REPO_URL}" "${DEPLOY_DIR}"
  info "Repository cloned to ${DEPLOY_DIR}."
fi

# ── Step 4: Copy .env ─────────────────────────────────────────────────────────
info "Step 4: Configuring environment file..."

ENV_FILE="${DEPLOY_DIR}/.env"
ENV_EXAMPLE="${DEPLOY_DIR}/.env.example"

if [[ -f "${ENV_FILE}" ]]; then
  info ".env already exists — skipping copy."
else
  if [[ ! -f "${ENV_EXAMPLE}" ]]; then
    die ".env.example not found at ${ENV_EXAMPLE}. Cannot continue."
  fi
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  chown "${DEPLOY_USER}:${DEPLOY_USER}" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  info ".env created from .env.example."

  # Generate a random SECRET_KEY and insert it
  GENERATED_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${GENERATED_KEY}|" "${ENV_FILE}"
  info "SECRET_KEY auto-generated and written to .env."

  warn "────────────────────────────────────────────────────────────────"
  warn "ACTION REQUIRED: Edit ${ENV_FILE} and set:"
  warn "  DATABASE_URL   — PostgreSQL connection string"
  warn "  POSTGRES_PASSWORD — must match the password in DATABASE_URL"
  warn "  DOMAIN         — your domain name (e.g. app.example.com)"
  warn "Then re-run this script to start the services."
  warn "────────────────────────────────────────────────────────────────"
  exit 0
fi

# ── Step 5: Build and start services ─────────────────────────────────────────
info "Step 5: Building and starting Docker services..."

cd "${DEPLOY_DIR}"
sudo -u "${DEPLOY_USER}" docker compose up -d --build
info "Services started."

# ── Step 6: Wait for PostgreSQL ───────────────────────────────────────────────
info "Step 6: Waiting for PostgreSQL to be ready (timeout: ${PG_READY_TIMEOUT}s)..."

elapsed=0
until sudo -u "${DEPLOY_USER}" docker compose exec -T db \
    pg_isready -U valgeougst -d valgeougst &>/dev/null; do
  if [[ $elapsed -ge $PG_READY_TIMEOUT ]]; then
    die "PostgreSQL did not become ready within ${PG_READY_TIMEOUT} seconds. Check: docker compose logs db"
  fi
  sleep 2
  elapsed=$((elapsed + 2))
  info "  ...waiting (${elapsed}s)"
done
info "PostgreSQL is ready."

# ── Step 7: Initialise database ───────────────────────────────────────────────
info "Step 7: Initialising database schema..."

if sudo -u "${DEPLOY_USER}" docker compose exec -T web \
    python scripts/init_db.py; then
  info "Database initialised successfully."
else
  warn "init_db.py returned a non-zero exit code."
  warn "If the schema already exists this may be harmless — check the output above."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo "  1. Create the admin user:"
echo "       docker compose exec web python scripts/create_admin.py \\"
echo "         --username admin --email admin@example.com --password CHANGE_ME"
echo ""
echo "  2. Obtain an SSL certificate:"
echo "       chmod +x scripts/init-letsencrypt.sh"
echo "       ./scripts/init-letsencrypt.sh yourdomain.example.com"
echo ""
echo "  3. Verify the app at https://\$(grep '^DOMAIN=' ${ENV_FILE} | cut -d= -f2)"
echo ""
echo "  RAM check (should stay under 6 GB):"
free -h
