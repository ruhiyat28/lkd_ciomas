#!/bin/bash
set -e
echo "================================================"
echo " Deploy LKD Ciomas — BUM Desa Bersama UPK"
echo "================================================"

# Buat folder data (postgres & uploads)
mkdir -p data/postgres data/uploads/{foto,ktp,kk,sku,penghasilan,jaminan,jaminan_docs}
echo "[deploy] Folder data siap"

# Pastikan .env ada
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[deploy] Dibuat file .env dari .env.example — sesuaikan SECRET_KEY & POSTGRES_PASSWORD bila perlu."
fi

# Stop container lama jika ada
docker compose down 2>/dev/null || true

# Build image baru
echo "[deploy] Building image..."
docker compose build --no-cache

# Jalankan
echo "[deploy] Starting containers..."
docker compose up -d

# Tunggu sampai sehat
echo "[deploy] Menunggu aplikasi siap (max 90 detik)..."
for i in $(seq 1 18); do
    sleep 5
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' lkd_ciomas_app 2>/dev/null || echo "starting")
    echo "  ... $((i*5))s — status: $STATUS"
    if [ "$STATUS" = "healthy" ]; then
        echo ""
        echo "✓ Aplikasi berjalan! Buka: http://localhost"
        echo "  Login: admin / admin123"
        exit 0
    fi
done

echo ""
echo "⚠ Timeout — cek log dengan: docker compose logs app --tail=50"
