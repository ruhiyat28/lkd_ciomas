# Panduan Deploy — BUM Desa Bersama UPK Ciomas LKD

Aplikasi versi 2.3 ini menggunakan **PostgreSQL** sebagai database
(sebelumnya SQLite). PostgreSQL akan otomatis ikut dijalankan oleh
`docker compose` sebagai service tersendiri — Anda **tidak perlu**
install PostgreSQL secara manual.

---

## A. Deploy di Linux / WSL (Windows)

### Langkah 1 — Salin ke WSL / server
```bash
cp /mnt/c/Users/<NAMA_USER>/Downloads/lkd_ciomas_v2.3.tar.gz ~/
cd ~ && tar -xzf lkd_ciomas_v2.3.tar.gz && cd lkd_ciomas
```

### Langkah 2 — Atur secret (sekali saja)
```bash
cp .env.example .env
nano .env       # ganti SECRET_KEY dan POSTGRES_PASSWORD bila perlu
```

### Langkah 3 — Deploy
```bash
bash deploy.sh
```

Tunggu sampai muncul pesan `✓ Aplikasi berjalan!`. Saat pertama kali
deploy, container `db` akan inisialisasi PostgreSQL dan `app` akan
men-seed COA + admin default.

### Langkah 4 — Akses
- Browser: <http://localhost>
- Login awal: `admin` / `admin123` (segera ganti dari menu Pengaturan)

---

## B. Update versi (data tetap aman)
```bash
cd ~/lkd_ciomas
docker compose down
tar -xzf ~/lkd_ciomas_v2.x.tar.gz   # ekstrak versi baru
docker compose build --no-cache
docker compose up -d
```

Volume `./data/postgres` dan `./data/uploads` di-mount terpisah,
sehingga update kode tidak menghapus database / file upload.

---

## C. Backup & Restore

### Backup database
```bash
docker exec lkd_ciomas_db pg_dump -U lkdciomas lkd_ciomas \
  > backup-$(date +%F).sql
```

### Backup file upload
```bash
tar -czf uploads-$(date +%F).tar.gz data/uploads
```

### Restore database
```bash
cat backup-2026-01-15.sql | docker exec -i lkd_ciomas_db \
  psql -U lkdciomas -d lkd_ciomas
```

---

## D. Jika Docker belum terinstall di WSL
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## E. Troubleshooting

### Lihat log
```bash
docker compose logs app --tail=80     # log Flask
docker compose logs db --tail=30      # log PostgreSQL
docker compose logs nginx --tail=30   # log web server
```

### App tidak mau naik (timeout healthcheck)
```bash
docker compose down
docker compose up -d
docker compose ps     # cek status
```

### Reset DATA (database + upload) — HATI-HATI!
```bash
docker compose down
rm -rf data/postgres data/uploads
bash deploy.sh
```

### Migrasi dari versi lama (SQLite → PostgreSQL)
Jika sebelumnya pakai SQLite (`data/db/lkd_ciomas.db`), gunakan
`pgloader` atau ekspor manual via menu *Import & Export* di aplikasi
lama, lalu import ulang setelah upgrade.

---

## F. Struktur Folder
```
lkd_ciomas/
├── .env                       ← konfigurasi (tidak di-commit)
├── .env.example               ← template
├── data/
│   ├── postgres/              ← DATABASE — JANGAN DIHAPUS
│   └── uploads/               ← File upload nasabah — JANGAN DIHAPUS
├── app/                       ← Kode aplikasi Flask
├── nginx/                     ← Konfigurasi web server
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── deploy.sh / deploy.bat     ← Script deploy
└── PANDUAN_DEPLOY.md
```

## G. Login Default
| Username | Password | Role |
|----------|----------|------|
| admin    | admin123 | Administrator |

> Setelah login pertama, segera ubah password & buat user baru sesuai
> peran (Manajer LKD, Bagian Kredit, Bagian Keuangan, dst.) dari menu
> **Pengaturan → Manajemen User**.
