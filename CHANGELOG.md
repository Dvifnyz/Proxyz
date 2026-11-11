# Changelog

## [2.1.0] - 2026-11-11

- Rename Proxyx jadi Proxyz. Itu aja — nama doang, makanya minor.
  Sempat ke-publish sebagai v3.0.0, langsung gue tarik. Tag sama
  rilisnya udah dihapus.
- README ditulis ulang dari referensi FastAPI & uv, tambah
  CONTRIBUTING, SECURITY, Code of Conduct, template issue/PR,
  .editorconfig, docs/MIGRASI-2.1.md.
- Perintah lama `proxyx` masih jalan sampai v3.0.0 (shim, ngasih
  peringatan). `PROXYX_TOKEN` sama `X-Proxyx-Token` tetap dibaca.

## [2.0.0] - 2026-11-11

- API publik dibekuin dan didokumentasiin (docs/API.md).
- `config/webshare.json` format lama otomatis dimigrasi ke
  `{"api_keys"}`.

## [1.9.0] - 2026-11-11

- `proxyz doctor`: diagnosa instalasi (Python, config, sumber, pool,
  key Webshare, blacklist, output, disk, gateway).

## [1.8.0] - 2026-11-11

- `proxyz laporan` (output/laporan.md) + endpoint `/api/report`.

## [1.7.0] - 2026-11-11

- `proxyz blacklist add|remove|list`; blacklist dipakai pas panen
  & cek.
- `proxyz panen --tier cepat|sedang|lambat`.

## [1.6.0] - 2026-11-11

- `proxyz auto`: siklus panen -> cek -> ekspor berkala; `--sekali`
  buat cron.

## [1.5.0] - 2026-11-11

- Rate limit API (60/menit per IP, 429 + Retry-After) + audit JSONL.
- Listener SOCKS5 (`gateway --socks 1080`); UDP ASSOCIATE ditolak.

## [1.4.0] - 2026-11-11

- `proxyz sync-9router` (aman: insert-only, backup, dedup).
- Profil gateway `scraper` / `cepat` / `hemat`.
- Backup pool otomatis (maks 5) tiap ekspor.

## [1.3.0] - 2026-11-11

- `proxyz bench` + endpoint `/api/bench`.
- Dashboard v2 (tombol leak test + uji kecepatan, warna skor).
- `proxyz install-service` (systemd + Windows Task).

## [1.2.0] - 2026-11-11

- `config/proxyz.json` yang beneran dibaca kode.
- `/api/leak-test` + `proxyz test`; `/api/clash.yaml`.
- `proxyz update` (aman, via pip, fallback ke tags).

## [1.1.0] - 2026-11-11

- Skor kesehatan sumber + backoff 1 jam; `proxyz sources`.
- Residential multi-akun; signup semi-otomatis (validasi key live).
- Healer probe HTTP beneran (bukan cuma TCP).

## [1.0.0] - 2026-11-11

- Rilis pertama: harvester 35 sumber, checker async, gateway rotating
  + REST API + dashboard + PAC, WARP, ekspor TXT/JSON/CSV/Clash,
  residential via API resmi Webshare, Docker + CI.
