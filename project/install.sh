#!/bin/bash
# ============================================================
# INSTALL SCRIPT — LKD CIOMAS Dana Bergulir
# Ubuntu Server 20.04 / 22.04 / 24.04
# Jalankan sebagai root: sudo bash install.sh
# ============================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

APP_DIR="/opt/lkd_ciomas"
APP_USER="www-data"
LOG_DIR="/var/log/lkd_ciomas"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "=============================================="
echo "  BUM DESA BERSAMA UPK CIOMAS LKD"
echo "  Instalasi Sistem Pengelolaan Dana Bergulir"
echo "=============================================="
echo ""

# 1. Update & Install dependensi sistem
info "Menginstall dependensi sistem..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv python3-dev \
    libffi-dev libssl-dev gcc git curl \
    nginx > /dev/null 2>&1
log "Dependensi sistem terinstall"

# 2. Buat direktori aplikasi
info "Menyiapkan direktori..."
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$APP_DIR/instance"

# 3. Copy file aplikasi
info "Menyalin file aplikasi ke $APP_DIR..."
cp -r "$SOURCE_DIR/"* "$APP_DIR/"
log "File disalin"

# 4. Buat virtual environment
info "Membuat virtual environment Python..."
python3 -m venv "$APP_DIR/venv"
log "Virtual environment dibuat"

# 5. Install dependensi Python
info "Menginstall dependensi Python (harap tunggu)..."
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q
log "Dependensi Python terinstall"

# 6. Buat semua folder yang diperlukan (HARUS sebelum chmod)
info "Membuat folder upload dan instance..."
for folder in foto ktp kk sku penghasilan jaminan; do
    mkdir -p "$APP_DIR/app/static/uploads/$folder"
done
mkdir -p "$APP_DIR/instance"
log "Folder upload dibuat"

# 7. Set permission
info "Mengatur permission..."
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$LOG_DIR"
chmod -R 755 "$APP_DIR"
chmod -R 777 "$APP_DIR/app/static/uploads"
chmod -R 777 "$APP_DIR/instance"
log "Permission diatur"

# 8. Konfigurasi Gunicorn log dir
sed -i "s|/var/log/lkd_ciomas|$LOG_DIR|g" "$APP_DIR/gunicorn.conf.py"

# 9. Setup systemd service
info "Menginstall systemd service..."
cp "$APP_DIR/lkd_ciomas.service" /etc/systemd/system/
sed -i "s|/opt/lkd_ciomas|$APP_DIR|g" /etc/systemd/system/lkd_ciomas.service
systemctl daemon-reload
systemctl enable lkd_ciomas
systemctl start lkd_ciomas
log "Service aktif dan akan auto-start"

# 10. Konfigurasi Nginx
info "Mengkonfigurasi Nginx reverse proxy..."
SERVER_IP=$(hostname -I | awk '{print $1}')

cat > /etc/nginx/sites-available/lkd_ciomas << NGINX
server {
    listen 80;
    server_name $SERVER_IP _;

    client_max_body_size 20M;

    location /static/ {
        alias $APP_DIR/app/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/lkd_ciomas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t > /dev/null 2>&1 && systemctl reload nginx
log "Nginx dikonfigurasi"

# 11. Firewall
info "Mengatur firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp > /dev/null 2>&1 || true
    ufw allow 22/tcp > /dev/null 2>&1 || true
fi

# 12. Cek status
sleep 3
if systemctl is-active --quiet lkd_ciomas; then
    STATUS="${GREEN}RUNNING${NC}"
else
    STATUS="${RED}NOT RUNNING${NC}"
    warn "Service gagal start. Cek log: journalctl -u lkd_ciomas -n 50"
fi

echo ""
echo "=============================================="
echo -e "  ${GREEN}INSTALASI SELESAI!${NC}"
echo "=============================================="
echo ""
echo -e "  Status Service : $STATUS"
echo -e "  URL Akses      : ${BLUE}http://$SERVER_IP${NC}"
echo ""
echo "  Login Default:"
echo -e "    Username : ${YELLOW}admin${NC}"
echo -e "    Password : ${YELLOW}admin123${NC}"
echo ""
echo -e "  ${RED}PENTING: Segera ganti password admin setelah login pertama!${NC}"
echo ""
echo "  Direktori Aplikasi : $APP_DIR"
echo "  Log Aplikasi       : $LOG_DIR"
echo ""
echo "  Perintah berguna:"
echo "    sudo systemctl status lkd_ciomas    # Cek status"
echo "    sudo systemctl restart lkd_ciomas   # Restart"
echo "    sudo journalctl -u lkd_ciomas -f    # Lihat log live"
echo "=============================================="
