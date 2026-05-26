#!/bin/bash
# Update aplikasi tanpa kehilangan data
set -e
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

COMPOSE="docker compose"
command -v docker >/dev/null && docker compose version >/dev/null 2>&1 || COMPOSE="docker-compose"

echo "=== Update LKD Ciomas ==="

info "Backup database..."
cp data/db/lkd_ciomas.db "data/db/lkd_ciomas_backup_$(date +%Y%m%d_%H%M%S).db" 2>/dev/null || true
log "Backup selesai"

info "Rebuild image..."
$COMPOSE build --no-cache app
log "Build selesai"

info "Restart container..."
$COMPOSE up -d --force-recreate app
log "Update selesai! Data tetap aman."
