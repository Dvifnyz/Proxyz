# Changelog

Semua perubahan penting Proxyz dicatat di sini, mengikuti
[Keep a Changelog](https://keepachangelog.com/id/1.1.0/) dan
[Semantic Versioning](https://semver.org/lang/id/).

## [3.0.0] - 2026-11-11

### Diubah (breaking)

- **Nama tool diganti dari Proxyx menjadi Proxyz** (paket, CLI,
  config, env, header). Perintah lama `proxyx` dan `import proxyx`
  masih jalan sampai v4.0.0 sebagai shim deprecated (lihat
  [docs/MIGRASI-3.0.md](docs/MIGRASI-3.0.md)).
- `config/proxyx.json` -> `config/proxyz.json`.
- Env `PROXYX_TOKEN` -> `PROXYZ_TOKEN` (nama lama tetap dibaca).
- Header `X-Proxyx-Token` -> `X-Proxyz-Token` (nama lama tetap dibaca).
- Baris 9Router kini ditandai `Proxyz`; `--ganti` membersihkan baris
  nama lama `Proxyx` juga.

### Ditambahkan

- README standar repo besar, CHANGELOG, CONTRIBUTING, SECURITY,
  Code of Conduct, template issue/PR.
- Deskripsi & topik repo GitHub.

## [2.0.0] - 2026-11-11

### Ditambahkan

- API publik dibekukan & didokumentasikan (`docs/API.md`).
- Migrasi otomatis `config/webshare.json` format lama `{"api_key"}`
  ke `{"api_keys"}`.

## [1.9.0] - 2026-11-11

### Ditambahkan

- `proxyz doctor`: diagnosa instalasi (Python, config, sumber, pool,
  key Webshare, blacklist, output, disk, gateway).

## [1.8.0] - 2026-11-11

### Ditambahkan

- `proxyz laporan` (`output/laporan.md`) + endpoint `/api/report`.

## [1.7.0] - 2026-11-11

### Ditambahkan

- `proxyz blacklist add|remove|list`; blacklist dipakai saat panen & cek.
- `proxyz panen --tier cepat|sedang|lambat`.

## [1.6.0] - 2026-11-11

### Ditambahkan

- `proxyz auto`: siklus panen -> cek -> ekspor berkala; `--sekali`
  untuk cron.

## [1.5.0] - 2026-11-11

### Ditambahkan

- Rate limit API (60/menit per IP, 429 + Retry-After) + audit JSONL.
- Listener SOCKS5 (`gateway --socks 1080`); UDP ASSOCIATE ditolak.

## [1.4.0] - 2026-11-11

### Ditambahkan

- `proxyz sync-9router` (aman: insert-only, backup, dedup).
- Profil gateway `scraper` / `cepat` / `hemat`.
- Backup pool otomatis (maks 5) tiap ekspor.

## [1.3.0] - 2026-11-11

### Ditambahkan

- `proxyz bench` + endpoint `/api/bench`.
- Dashboard v2 (tombol leak test + uji kecepatan, warna skor).
- `proxyz install-service` (systemd + Windows Task).

## [1.2.0] - 2026-11-11

### Ditambahkan

- `config/proxyz.json` yang benar-benar dibaca kode.
- `/api/leak-test` + `proxyz test`; `/api/clash.yaml`.
- `proxyz update` (aman, via pip, fallback ke tags).

## [1.1.0] - 2026-11-11

### Ditambahkan

- Skor kesehatan sumber + backoff 1 jam; `proxyz sources`.
- Residential multi-akun; signup semi-otomatis (validasi key live).
- Healer probe HTTP beneran (bukan cuma TCP).

## [1.0.0] - 2026-11-11

### Ditambahkan

- Rilis pertama: harvester 35 sumber, checker async, gateway rotating
  + REST API + dashboard + PAC, WARP, ekspor TXT/JSON/CSV/Clash,
  residential via API resmi Webshare, Docker + CI.
