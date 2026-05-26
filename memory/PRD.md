# PRD — LKD Ciomas Mobile (Flutter)

## Original Problem Statement
> "saya sedang mengembangkan versi mobile dan saya menemukan beberapa fungsi belum berjalan sempurna, tolong cek lalu perbaiki. saya juga ingin desainnya buat lebih minimalis modern, kita bisa gunakan desain yang selaras dengan desain pada versi desktop"

Codebase: `lkdCiomas.rar` → extracted ke `/app/project/lkd_ciomas_v2.4/`.
Bagian mobile: `lkd_ciomas_mobile/` (Flutter 3.27+).

## Stack
- **Mobile**: Flutter 3.12+, Material 3, Riverpod 2.6, go_router 14.x, Dio 5
- **Backend**: Flask 3 + PostgreSQL (dipakai mobile via REST `/api/*` di `https://apps.ciomas.web.id/api`)

## User Personas
1. **Nasabah** — tabungan, pinjaman, UMKM, profile
2. **Kader Desa** — penagihan, nasabah, pinjaman
3. **Penagih** — penagihan, bonus
4. **Verifikator** — verifikasi pinjaman, cari nasabah
5. **Admin/Manajer** — semua + ACC pembayaran + statistik

## Core Requirements
- JWT auth via `/api/auth/login`
- Bottom navigation role-based
- Desain minimalis modern selaras desktop (warna primary `#1A56DB`) dengan rasa bank digital (BCA-style: kartu saldo gradient biru, pill chips, soft shadows)

## What's Been Implemented (Session 5/10/2026)

### Bug Fixes
1. **🔴 Router tidak react ke auth state** — Ditambahkan `refreshListenable` via custom `ChangeNotifier` yang mendengar `authProvider`. Splash, login dan logout sekarang auto-navigate.  
   _File: `lib/core/router/app_router.dart`_
2. **🔴 `Pinjaman.fromJson` crash** — Field `nasabah` API berupa String (nama). Sebelumnya dipanggil sebagai Map → TypeError. Diperbaiki: handle String / Map / null; tambah fallback `nasabah_detail`.  
   _File: `lib/models/pinjaman.dart`_
3. **🔴 `NasabahFormScreen` tidak punya field Desa** — Backend menolak create. Sekarang form punya dropdown Desa (dari `/api/config` atau fallback list), validator wajib, juga date picker tanggal lahir & jenis kelamin.  
   _File: `lib/features/nasabah/nasabah_form_screen.dart`_
4. **🟡 `UmkmKatalogScreen` duplicate import** — Import `currency_format.dart` ganda, dibersihkan.
5. **🟡 `isSeller` logic salah** — Sekarang cek `/umkm/penjual/status` (status `aktif`/`disetujui`). Nasabah yang belum daftar dapat tombol "Daftar Penjual" di app bar; yang sudah aktif dapat menu Toko/Pesanan.

### Redesign — Minimalis Modern BCA-Style
- **`AppColors`**: tambah `primaryDeep`, `primarySoft`, `accent` (kuning emas), gradient kartu (`cardGradient`, `cardGradientSoft`).
- **`AppTheme`**: M3, `NavigationBarThemeData` dengan pill indicator, input fields tanpa border (soft fill), card elevation 0 + soft shadow, AppBar putih dengan teks gelap (bukan biru penuh seperti versi lama).
- **`AppShadows`** utility (sm, md, brand) untuk konsistensi shadow.

#### Screen yang sudah direvisi
| Screen | Fokus |
|---|---|
| Splash | Logo dalam kontainer floating, gradient biru deep, dekoratif circles |
| Login | Hero header gradient + curved bottom, form card terpisah dengan shadow |
| Shell (BottomNav) | `NavigationBar` M3 dengan pill indicator `primarySoft` |
| Dashboard | Header sapaan + inisial avatar, kartu saldo gradient ala kartu kredit (BCA-style) dengan toggle show/hide, quick action grid, stat grid untuk staff, pengumuman card minimalis |
| Tabungan | Kartu saldo BCA-style dengan no-rekening pill + toggle hide/show, action setor/tarik, breakdown card, mutasi list dengan icon up/down |
| Profile | Header card gradient dengan avatar inisial, data nasabah dengan info rows, menu kategori dengan icon color-coded |
| Pinjaman List | Card baru dengan icon avatar, status pill, jumlah & sisa side-by-side |
| Penagihan List | Card warna-coded (merah jika nunggak), pill nunggak |
| Nasabah List | Card minimalis dengan avatar inisial + status pill |
| Verifikasi Form | Choice chip dengan icon (bukan emoji) |
| ACC Pembayaran | Status pill dengan icon (bukan emoji ⏳) |

### Tidak Diubah (sudah cukup baik atau tidak prioritas)
- Forms kompleks (pinjaman form, pembayaran form, tabungan setor) — masih fungsional dengan style baru otomatis lewat theme
- Detail screens (nasabah detail, pinjaman detail, jadwal angsuran) — UI lama, dapat warna baru via theme
- UMKM detail, pesanan saya/masuk, daftar penjual — utility screens, dapat warna baru lewat theme

## Prioritized Backlog (P0/P1/P2)

### P0 — Next Session
- [ ] Build APK & user test on device (perlu `flutter build apk --release` — tidak bisa dijalankan di sandbox ini)
- [ ] Redesign detail screens (`nasabah_detail`, `pinjaman_detail`) dengan card minimalis baru
- [ ] Redesign forms (`pinjaman_form`, `pembayaran_form`, `tabungan_setor`) — saat ini dapat warna baru otomatis dari theme

### P1
- [ ] Implementasi notifikasi push (FCM sudah terdaftar di pubspec, perlu wiring)
- [ ] Search dengan debounce di nasabah_list (saat ini cuma onSubmitted)
- [ ] Skeleton loader (shimmer dependency sudah ada) menggantikan spinner

### P2
- [ ] Animasi staggered untuk dashboard
- [ ] Dark mode (theme sudah pakai colorSchemeSeed, tinggal extend)
- [ ] Offline queue untuk pembayaran (penagih di lapangan)

## Build & Run Instructions

```bash
# Di sistem dengan Flutter SDK terpasang:
cd /app/project/lkd_ciomas_mobile

# Pastikan dependencies sinkron
flutter pub get

# Test build (debug)
flutter run

# Build APK release
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

Catatan: container ini tidak punya Flutter SDK, jadi perubahan harus di-build di lokal/CI Anda.

## Key API Endpoints
| Endpoint | Method | Auth | Fungsi |
|---|---|---|---|
| `/api/auth/login` | POST | — | Login |
| `/api/auth/register` | POST | — | Daftar nasabah |
| `/api/auth/me` | GET | JWT | Profile + nasabah + rekening |
| `/api/auth/change-password` | POST | JWT | Ganti password |
| `/api/config` | GET | — | Desa list, tenor options |
| `/api/dashboard` | GET | JWT | Stats + rekap + pengumuman |
| `/api/nasabah` | GET/POST | JWT | List/create nasabah |
| `/api/nasabah/:id` | GET/PUT | JWT | Detail/update |
| `/api/nasabah/:id/approve` | POST | JWT | Approve calon |
| `/api/pinjaman` | GET/POST | JWT | List/create pinjaman |
| `/api/pinjaman/hitung-angsuran` | POST | JWT | Kalkulasi simulasi |
| `/api/pinjaman/:id/verifikasi` | PUT | JWT | Verifikasi |
| `/api/pembayaran` | GET/POST | JWT | List/create pembayaran |
| `/api/pembayaran/:id/acc` | POST | JWT | ACC pembayaran |
| `/api/tabungan` | GET | JWT | Detail rekening |
| `/api/tabungan/setor` | POST | JWT | Setor |
| `/api/tabungan/tarik` | POST | JWT | Tarik |
| `/api/bonus/saya` | GET | JWT | Bonus petugas |
| `/api/umkm/produk` | GET/POST | JWT | Katalog/tambah |
| `/api/umkm/penjual/status` | GET | JWT | Status seller |
| `/api/umkm/pesanan` | GET/POST | JWT | Pesanan |
