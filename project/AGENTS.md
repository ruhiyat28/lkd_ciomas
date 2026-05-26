# AGENTS.md — LKD Ciomas

## Stack
Flask 3 + SQLAlchemy + PostgreSQL (Docker) + nginx. No test suite, no linter.

## App entrypoint
`run.py` → `create_app()` in `app/__init__.py`. All models in `app/models.py`. All routes in `app/routes/`.

## Startup behavior (important)
Every startup via `entrypoint.sh` (Docker) or direct `create_app()`:
1. Waits for PostgreSQL if `DATABASE_URL` points to it
2. Runs schema migrations via `app/utils/db_migrate.py` (idempotent, safe to re-run)
3. Seeds COA chart of accounts if empty
4. Auto-creates `RekeningTabungan` for any `Nasabah` that lacks one
5. Seeds admin user (username: `admin`, password: `admin123`) if not exists
6. Seeds default `Pengaturan` rows
7. Starts Gunicorn on port 5000

## Data directories
- `data/postgres/` — PostgreSQL data (**never delete on upgrade**)
- `data/uploads/` — uploaded files (KK, KTP, foto, dll) (**never delete on upgrade**)
- `instance/lkd_ciomas.db` — SQLite fallback if no PostgreSQL

## Deploy
- **Docker**: `bash deploy.sh` → builds + starts all 3 containers (db, app, nginx). Access <http://localhost>.
- **Bare metal**: `sudo bash install.sh` → sets up venv, systemd service, nginx reverse proxy.

## Config
- `.env` file (gitignored) — set `SECRET_KEY`, `POSTGRES_*`
- `config.py` — app config (secret, upload folder, DESA_LIST, KOLEK_CADANGAN, tenor options)
- `docker-compose.yml` — sets `DATABASE_URL` automatically from env vars

## Upload folders (auto-created on startup)
`foto`, `ktp`, `kk`, `sku`, `penghasilan`, `jaminan`, `jaminan_docs`, `umkm`

## Key calculation functions (in `app/models.py`)
`hitung_angsuran_bulat(jumlah, tenor, jasa_persen)` — rounds principal up to nearest 100, calculates flat interest, returns dict with `pokok`, `jasa`, `total`, `pokok_terakhir`, `total_terakhir`.

## Custom Jinja2
- Filter `| number_format` — formats number with `.` as thousands separator (e.g. `1000000` → `1.000.000`)
- Test `startswith` — checks string prefix

## Run locally (non-Docker)
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env if needed (SECRET_KEY, DATABASE_URL)
python run.py
```

## Logs
- Docker: `docker compose logs app --tail=80`
- Bare metal: `sudo journalctl -u lkd_ciomas -f`
