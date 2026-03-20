#!/bin/bash
# =============================================================================
# scripts/init-letsencrypt.sh — Obtain Let's Encrypt certificate and activate
#                               the SSL Nginx config.
#
# USAGE:
#   bash scripts/init-letsencrypt.sh <domain>
#
# EXAMPLE:
#   bash scripts/init-letsencrypt.sh yourdomain.com
#
# PREREQUISITES:
#   - Docker Compose services are running (at minimum: web, nginx with
#     nginx-nossl.conf so the ACME HTTP challenge can be served)
#   - Port 80 is reachable from the internet
#   - DNS A record for <domain> points to this server's public IP
#
# WHAT THIS SCRIPT DOES:
#   1. Validates that a domain argument was supplied.
#   2. Checks whether a certificate for the domain already exists.
#   3. If no certificate exists, runs Certbot (webroot plugin) inside the
#      certbot Docker container to obtain one.
#   4. Replaces the DOMAIN placeholder in nginx/nginx.conf with the real domain.
#   5. Reloads Nginx so the SSL config takes effect.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Validate arguments
# ---------------------------------------------------------------------------
if [[ $# -lt 1 || -z "${1:-}" ]]; then
    error "No domain supplied.\nUsage: bash $0 <domain>\nExample: bash $0 yourdomain.com"
fi

DOMAIN="$1"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
WEBROOT_PATH="/var/www/certbot"
NGINX_CONF="$(dirname "$0")/../nginx/nginx.conf"
NGINX_CONF="$(realpath "$NGINX_CONF")"

info "Domain : ${DOMAIN}"
info "Cert   : ${CERT_PATH}"
info "Config : ${NGINX_CONF}"

# ---------------------------------------------------------------------------
# 2. Check whether the certificate already exists
# ---------------------------------------------------------------------------
if docker compose run --rm certbot certificates 2>/dev/null | grep -q "${DOMAIN}"; then
    info "Certificate for ${DOMAIN} already exists — skipping Certbot."
else
    info "No certificate found for ${DOMAIN}. Running Certbot..."

    # Prompt for email (used for expiry notifications)
    read -rp "Enter your email address for Let's Encrypt notifications: " LE_EMAIL
    if [[ -z "${LE_EMAIL}" ]]; then
        error "Email address is required for Let's Encrypt registration."
    fi

    # Run certbot certonly with the webroot plugin.
    # The certbot service in docker-compose.yml must mount:
    #   ./certbot/conf  -> /etc/letsencrypt
    #   ./certbot/www   -> /var/www/certbot
    docker compose run --rm certbot certonly \
        --webroot \
        --webroot-path="${WEBROOT_PATH}" \
        --email "${LE_EMAIL}" \
        --agree-tos \
        --no-eff-email \
        -d "${DOMAIN}"

    info "Certificate obtained successfully."
fi

# ---------------------------------------------------------------------------
# 3. Replace DOMAIN placeholder in nginx/nginx.conf
# ---------------------------------------------------------------------------
if [[ ! -f "${NGINX_CONF}" ]]; then
    error "nginx.conf not found at ${NGINX_CONF}. Run this script from the project root or ensure the file exists."
fi

if grep -q "DOMAIN" "${NGINX_CONF}"; then
    info "Replacing DOMAIN placeholder with '${DOMAIN}' in ${NGINX_CONF}..."
    # Use a temp file to avoid in-place sed portability issues (macOS vs Linux)
    TMP_CONF="$(mktemp)"
    sed "s/DOMAIN/${DOMAIN}/g" "${NGINX_CONF}" > "${TMP_CONF}"
    mv -f "${TMP_CONF}" "${NGINX_CONF}"
    info "Placeholder replaced."
else
    info "No DOMAIN placeholder found in ${NGINX_CONF} — already substituted or using a custom config."
fi

# ---------------------------------------------------------------------------
# 4. Reload Nginx
# ---------------------------------------------------------------------------
info "Reloading Nginx..."
if docker compose exec nginx nginx -t; then
    docker compose exec nginx nginx -s reload
    info "Nginx reloaded successfully."
else
    error "Nginx config test failed. Fix the config and reload manually:\n  docker compose exec nginx nginx -s reload"
fi

info "Done. Visit https://${DOMAIN} to verify SSL is working."
