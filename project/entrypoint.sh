#!/bin/sh
set -e

echo "============================================"
echo " BUM Desa Bersama UPK Ciomas LKD"
echo " Starting application..."
echo "============================================"

# ── Tunggu PostgreSQL siap (jika DATABASE_URL postgres) ──────
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "^postgres"; then
    HOST=$(echo "$DATABASE_URL" | sed -E 's#.*@([^:/]+).*#\1#')
    PORT=$(echo "$DATABASE_URL" | sed -E 's#.*@[^:]+:([0-9]+).*#\1#')
    : "${PORT:=5432}"
    echo "[startup] Menunggu PostgreSQL $HOST:$PORT ..."
    i=0
    until python3 -c "import socket,sys;s=socket.socket();
try:
 s.settimeout(2); s.connect(('$HOST',int('$PORT'))); s.close()
except Exception: sys.exit(1)" 2>/dev/null; do
        i=$((i + 1))
        if [ "$i" -gt 60 ]; then
            echo "[startup] PostgreSQL belum siap setelah 60s, lanjut tetap mencoba."
            break
        fi
        sleep 1
    done
    echo "[startup] PostgreSQL OK."
fi

# ── Init database, seed COA, rekening, dll ───────────────────
python3 - << 'PYEOF'
import sys, traceback

try:
    from app import create_app
    from app.models import db, Nasabah, RekeningTabungan, Pengaturan

    app = create_app()
    print("[startup] App created OK")

    with app.app_context():
        # Seed COA jika belum ada
        try:
            from app.utils.coa_seed import seed_coa
            seed_coa()
        except Exception as e:
            print(f"[startup] COA seed info: {e}")

        # Auto-buat rekening tabungan untuk nasabah yang belum punya
        try:
            buat = 0
            for n in Nasabah.query.all():
                if not RekeningTabungan.query.filter_by(nasabah_id=n.id).first():
                    db.session.add(RekeningTabungan(
                        nasabah_id  = n.id,
                        no_rekening = f'TAB-{n.nasabah_id}'
                    ))
                    buat += 1
            if buat:
                db.session.commit()
                print(f"[startup] Rekening tabungan dibuat: {buat}")
        except Exception as e:
            db.session.rollback()
            print(f"[startup] Rekening info: {e}")

        print("[startup] Database siap.")

except Exception as e:
    print(f"[startup] ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo "[startup] Memulai Gunicorn..."
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    run:app
