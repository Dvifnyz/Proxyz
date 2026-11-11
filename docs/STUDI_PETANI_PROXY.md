# Studi repo asli: itzluthfi/petani-proxy v1.2.0

Ringkasan bedah read-only (clone 2026-11-11, ±9.643 baris). Tidak ada kode
yang disalin ke Proxyz — yang dipakai ulang hanya ide dan pola yang terbukti
benar, dengan sumbernya dicatat. Nilai sensitif (kredensial apa pun yang
ada di repo asli) sengaja TIDAK ditulis di sini.

## Yang bagus dan dipakai ulang (dengan perbaikan)

- **Daftar 30 sumber proxy** (`config/sources.json`) — ditambah 5 sumber
  jadi 35 di Proxyz.
- **Regex IPv4 ketat + dedup `protocol://ip:port`** (`fetcher.py`).
- **Klasifikasi anonimitas** (`checker.py`): transparent bila IP asli
  bocor, anonymous bila ada header jejak proxy, elite bila bersih.
- **Round-robin + sticky session 10 menit + retry 3x + PAC** (`server.py`).
- **Bridge SOCKS/auth → HTTP lokal** (`proxy_bridge.py`) — pola ini
  dipakai Proxyz untuk gateway SOCKS upstream.
- **Registrasi WARP via API resmi Cloudflare** (`warp_generator.py`) —
  sah, tanpa captcha.
- **Format ekspor** TXT/JSON/CSV (`exporter.py`).

## Cacat yang ditemukan dan TIDAK dibawa ke Proxyz

1. **Docker rusak**: `CMD` memakai flag `--gateway --port --background`
   yang tidak ada di argparse — container langsung exit.
2. **Updater berbahaya**: menjalankan `auto_run_commands` dari
   `version.json` remote via `shell=True`, plus `git reset --hard`
   yang menghapus perubahan lokal tanpa konfirmasi.
3. **Kredensial hardcoded** sebagai fallback di modul farm akun —
   pola ini dilarang di Proxyz (kredensial hanya via env/file lokal 0600).
4. **Gateway tanpa autentikasi**, CORS `*`, endpoint farm bisa dipicu
   dari browser mana pun yang bisa mencapai port lokal.
5. **TLS dimatikan** (`verify=False` / `ssl=False`) di fetcher & validator.
6. **Tiga jalur checker duplikat** (klasik / fast / healer) dengan default
   berbeda; **dua daftar sumber** (sources.json vs FAST_SOURCES hardcode).
7. **Filter negara menyesatkan**: hanya efektif di proxyscrape, tapi
   README mengklaim "150+ negara".
8. **GeoIP per proxy** (satu request per IP, rate-limit 45/menit) —
   Proxyz memakai batch 100 IP.
9. **Health check sequential** (pool 30 × timeout 3 dtk ≈ 90 dtk).
10. **Kode mati**: modul farm yang yatim (tidak diimpor siapa pun),
    aset stealth yang tidak direferensikan, variabel `.env` yang tidak
    dibaca kode mana pun, versi 1.0.0/1.1.0/1.2.0 di lima tempat.
11. **Sync 9Router destruktif**: menghapus baris SQLite milik tool lain.
12. **Output contoh ikut ter-commit**, termasuk file konfigurasi WARP.
13. **Hanya 4 test case** untuk seluruh repo.

## Keputusan desain Proxyz dari studi ini

- Satu pipeline async (aiohttp), satu `sources.json`, satu sumber versi.
- TLS tetap nyala (system CA store). Logging, bukan `except: pass`.
- Geo batch, health check paralel, skor kualitas proxy.
- Updater aman: tanpa eksekusi perintah remote (rencana Tahap 4:
  update via `pip install` dari release + checksum).
- Residential via API resmi Webshare + import manual — bukan farm akun
  otomatis + pemecah captcha (rapuh, akun cepat di-banned, melanggar ToS).
- Docker diperbaiki dan diuji di CI. `output/` di-gitignore.
