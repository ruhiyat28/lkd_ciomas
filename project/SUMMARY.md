# LKD Ciomas — Ringkasan Pengembangan

## Stack
- **Web**: Flask 3 + SQLAlchemy + PostgreSQL (Docker) + nginx + Jinja2 templates
- **Mobile**: Flutter 3.27.4 (APK) — glassmorphism UI, JWT auth
- **API**: REST JSON endpoints di `/api/*` — flask-jwt-extended

## Struktur Proyek

```
lkd_ciomas_v2.4/
├── app/
│   ├── __init__.py          # create_app()
│   ├── models.py             # Semua model SQLAlchemy
│   ├── routes/
│   │   ├── api/              # REST API (9 module)
│   │   │   ├── __init__.py   # Blueprint api_bp, JWT, role_required, get_current_user
│   │   │   ├── auth.py       # Login, register, me, change-password
│   │   │   ├── nasabah.py    # CRUD + approve
│   │   │   ├── pinjaman.py   # CRUD + hitung angsuran
│   │   │   ├── pembayaran.py # Create + list
│   │   │   ├── tabungan.py   # Rekening, setor, tarik
│   │   │   ├── dashboard.py  # Dashboard stats + rekap desa
│   │   │   ├── upload.py     # Ganti foto/ktp/kk
│   │   │   ├── fcm.py        # Firebase token
│   │   │   ├── umkm.py       # 15 endpoints UMKM
│   │   │   └── bonus.py      # GET /api/bonus/saya (NEW)
│   │   ├── main.py, pinjaman.py, pembayaran.py, tabungan.py, ...
│   │   └── bonus.py          # Web routes bonus
│   └── templates/
│       ├── base.html          # Sidebar, bottom nav, dropdown profil
│       └── main/dashboard.html # Dashboard web (nasabah + staff)
├── docker-compose.yml
├── deploy.sh
├── entrypoint.sh
├── config.py
├── AGENTS.md
├── SUMMARY.md                 # ← file ini
└── lkd_ciomas_app/
    ├── pubspec.yaml
    ├── lib/
    │   ├── config.dart        # baseUrl, desa list, tenor
    │   ├── theme.dart         # AppColors, AppShadows, AppRadius, AppGradients
    │   ├── services/
    │   │   └── api_service.dart # HTTP client (singleton), ApiResponse
    │   ├── models/
    │   │   ├── user_model.dart
    │   │   ├── nasabah_model.dart
    │   │   ├── pinjaman_model.dart  # + noHp, noHpPasangan
    │   │   ├── tabungan_model.dart
    │   │   ├── dashboard_model.dart
    │   │   └── umkm_model.dart
    │   └── screens/
    │       ├── login_screen.dart        # Particle anim, glassmorphism card
    │       ├── register_screen.dart     # NEW — form daftar nasabah
    │       ├── home_screen.dart         # Main shell: AppBar + bottom nav + popup menu
    │       ├── dashboard_screen.dart    # Staff: quick actions; Nasabah: Pinjaman+Tabungan cards
    │       ├── nasabah_list_screen.dart # Compact: ID, Nama, Desa, Lihat
    │       ├── nasabah_detail_screen.dart
    │       ├── nasabah_form_screen.dart
    │       ├── pinjaman_list_screen.dart # Compact: SPK, Nasabah, Jml, Lihat
    │       ├── pinjaman_detail_screen.dart # Single Scaffold, jadwal angsuran
    │       ├── pinjaman_form_screen.dart
    │       ├── pembayaran_form_screen.dart
    │       ├── pembayaran_list_screen.dart # Compact + search
    │       ├── tabungan_screen.dart     # Tanpa Scaffold (embedded sbg tab)
    │       ├── tunggakan_screen.dart    # Search + WA button + glassmorphism
    │       ├── bonus_screen.dart        # NEW — daftar bonus petugas
    │       ├── umkm_screen.dart         # Tanpa Scaffold (embedded sbg tab)
    │       ├── umkm_produk_form_screen.dart
    │       ├── umkm_pesanan_detail_screen.dart
    │       ├── profile_screen.dart
    │       └── change_password_screen.dart
    ├── assets/
    │   ├── logo.png
    │   ├── bg-login.png
    │   └── fonts/
    │       ├── PlusJakartaSans-Variable.ttf
    │       └── DMMono-*.ttf
    └── build/app/outputs/flutter-apk/app-release.apk
```

## Riwayat Perubahan

### Sesi 1 — Setup Awal
- Rest API backend (`app/routes/api/` — 9 module)
- Flutter app dengan 15 screens, 6 models, 1 service
- Arsitektur bottom nav 6 tab, sidebar dark
- Login screen glassmorphism + floating particles

### Sesi 2 — Redesign UI
- Font PlusJakartaSans + DMMono (bundled, tanpa google_fonts)
- Glassmorphism di semua cards
- Sidebar 248px matching web CSS
- Login screen redesign (gradient bg, particle anim)

### Sesi 3 — Fitur UMKM
- API UMKM (15 endpoints: penjual, produk, pesanan)
- 4 screen UMKM (produk, toko, pesanan, detail)
- API bonus (GET /api/bonus/saya)

### Sesi 4 — Simplifikasi Menu Staf (terbaru)
**Web (base.html):**
- Staff bottom nav: ~~Beranda~~, Nasabah, Pinjaman, Bayar, Tagih
- Nasabah bottom nav: Beranda, Pinjaman, Tabungan, UMKM
- "Pengaturan Pembayaran" hanya untuk admin/manajer

**Flutter:**
- Sidebar **dihapus** — navigasi via bottom nav + popup menu avatar
- Staff bottom nav: Nasabah, Pinjaman, Bayar, Tagih (4 tab)
- Nasabah bottom nav: Beranda, Pinjaman, Tabungan, UMKM
- Popup avatar: Profil, Bonus Saya, Ganti Password, Riwayat, Keluar
- List compact (nasabah, pinjaman, pembayaran)
- Dashboard: staff = aksi cepat; nasabah = kartu Pinjaman Saya + Tabungan Saya

### Sesi 5 — Tagih + WA
- **TunggakanScreen**: search by nama/SPK, WA button, glassmorphism cards
- API pinjaman: tambah `no_hp`, `no_hp_pasangan`
- `PinjamanModel`: tambah `noHp`, `noHpPasangan`
- WA message template seperti web

### Sesi 6 — Login + Register + Dashboard Nasabah
- **RegisterScreen** baru — form lengkap, POST `/api/auth/register`
- Login "Daftar Sekarang" → navigasi ke RegisterScreen
- **Dashboard nasabah**: 2 gradient cards (Pinjaman Saya, Tabungan Saya) + pengumuman
- Login card diperkecil agar tidak overflow layar kecil

### Sesi 7 — Bug Fixes
- Hapus Scaffold+AppBar dari `TabunganScreen` & `UmkmScreen` (duplicate header)
- `labelBehavior: alwaysShow` → `onlyShowSelected` (tab overflow)
- Hapus `height: 60` dari NavigationBar
- `PinjamanDetailScreen`: satu Scaffold dengan body bersyarat (fix white screen)

## Catatan Penting

### Login
- `POST /api/auth/login` → `{success, data: {token, user}}`
- Token disimpan di `SharedPreferences` key `jwt_token`
- User data di `SharedPreferences` key `user_data`
- Register via `POST /api/auth/register` (tanpa JWT)

### Role & Nav
| Role | Bottom Nav Tabs | Akses Khusus |
|---|---|---|
| admin/manajer | Nasabah, Pinjaman, Bayar, Tagih | +
| kader/staf/dll | Nasabah, Pinjaman, Bayar, Tagih | Bonus Saya di popup |
| nasabah | Beranda, Pinjaman, Tabungan, UMKM | Dashboard sendiri |

### Tab body vs Pushed screen
- **Tab body** (tidak punya Scaffold sendiri): dashboard, nasabah_list, pinjaman_list, bayar, tagih, tabungan, umkm
- **Pushed screen** (punya Scaffold sendiri): detail_nasabah, detail_pinjaman, profile, change_password, bonus, pembayaran_list, register

### API Endpoint Kunci
| Endpoint | Method | Auth | Fungsi |
|---|---|---|---|
| `/api/auth/login` | POST | — | Login |
| `/api/auth/register` | POST | — | Daftar nasabah baru |
| `/api/auth/me` | GET | JWT | User info + rekening |
| `/api/dashboard` | GET | JWT | Stats, rekap, rekening, pengumuman |
| `/api/pinjaman` | GET | JWT | List pinjaman (+ `no_hp`, `no_hp_pasangan`) |
| `/api/bonus/saya` | GET | JWT | Bonus petugas + pembina |
| `/api/pembayaran` | GET | JWT | Riwayat bayar |

### Build APK
```bash
source setenv.sh && cd lkd_ciomas_app && flutter build apk --release
```
Output: `lkd_ciomas_app/build/app/outputs/flutter-apk/app-release.apk`

### Deploy Web
```bash
bash deploy.sh
```
3 container: app, db (postgres:15-alpine), nginx

### Key File Relations
- `app/templates/base.html:1868-1907` — bottom nav mobile web
- `app/templates/base.html:1757-1788` — dropdown profil
- `lkd_ciomas_app/lib/screens/home_screen.dart:62-77` — tab builder (role-based)
- `lkd_ciomas_app/lib/screens/home_screen.dart:233-251` — popup menu avatar
- `lkd_ciomas_app/lib/theme.dart` — semua warna, radius, shadow
- `app/routes/api/dashboard.py:72-96` — data khusus nasabah (rekening, pengumuman, ajuan)
- `app/routes/api/pinjaman.py:51-77` — response pinjaman (tambah field via edit)
