# Proxyz

Tool proxy buat panen proxy publik, ngecek mana yang hidup, terus
disajiin lewat gateway lokal. Ada WARP sama residential juga.

[![Release](https://img.shields.io/github/v/release/Dvifnyz/Proxyz)](https://github.com/Dvifnyz/Proxyz/releases)
[![CI](https://github.com/Dvifnyz/Proxyz/actions/workflows/ci.yml/badge.svg)](https://github.com/Dvifnyz/Proxyz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/Dvifnyz/Proxyz)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)

Dulu namanya Proxyx, ganti jadi Proxyz di v2.1.0 biar sama kayak
nama repo. Perintah lama (`proxyx`, `python -m proxyx`,
`import proxyx`) masih jalan sampai v3.0.0, cuma ngasih peringatan.
Panduan pindah: [docs/MIGRASI-2.1.md](docs/MIGRASI-2.1.md).

## Kenapa gue bikin ini

Gue bedah repo [petani-proxy-nya itzluthfi](https://github.com/itzluthfi/petani-proxy)
tanggal 11 November 2026, sekitar 8.600 baris. Idenya bagus — panen
proxy, gateway, WARP — tapi pas dibaca isinya banyak yang ngaco:
TLS dimatiin, updater-nya ngejalanin perintah dari server, gateway
tanpa auth, Docker-nya langsung exit karena flag-nya nggak ada di
argparse, ada tiga checker yang saling duplikat.

Jadi gue tulis ulang dari nol. Yang benernya diambil, yang rusaknya
diperbaiki. Catatan lengkap bedahnya ada di
[docs/STUDI_PETANI_PROXY.md](docs/STUDI_PETANI_PROXY.md).

Yang sengaja nggak gue bikin: pemecah captcha otomatis sama farm
akun massal. Bukan karena nggak bisa — karena akun hasil farm itu
umurnya pendek. Cepet di-ban, IP-nya ikut mati, tool-nya jadi
nggak kepake. Yang main bersih itu yang awet.

## Install

Butuh Python 3.9 ke atas.

```bash
pip install proxyz
```

Atau pakai pipx biar nggak ngotorin environment:

```bash
pipx install proxyz
```

Dari source:

```bash
git clone https://github.com/Dvifnyz/Proxyz.git
cd Proxyz
pip install -e .
```

Docker:

```bash
docker build -t proxyz .
docker run -p 8888:8888 proxyz
```

## Cara pakai

```bash
python -m proxyz panen --jumlah 20     # panen + cek 20 proxy hidup
python -m proxyz gateway               # gateway di http://127.0.0.1:8888
curl -x http://127.0.0.1:8888 http://api.ipify.org
```

Tanpa argumen, `python -m proxyz` ngebuka menu interaktif.

Ini output beneran dari mesin gue, 11 November 2026:

```
$ python -m proxyz sources

  SUMBER                                                HASIL  GAGAL  STATUS
  https://raw.githubusercontent.com/zevtyardt/proxy-   128468      0  aktif
  https://raw.githubusercontent.com/B4RC0DE-TM/proxy     6370      0  aktif
  https://raw.githubusercontent.com/TheSpeedX/PROXY-     5354      0  aktif
```

Satu kali panen dapat 68.986 kandidat. Yang hidup berapa? Tergantung
hari. Proxy gratisan itu mayoritas mati — itu normal, bukan bug.
Jangan kaget kalau dapat 0 di jaringan yang ngeblok TCP langsung
(misalnya sandbox). Di laptop biasa harusnya jalan.

## Perintah

| Perintah | Buat apa |
|---|---|
| `proxyz panen [--jumlah 20] [--negara ID] [--protokol all] [--tier cepat] [--geo]` | Panen + cek proxy hidup, ekspor ke `output/` |
| `proxyz cek <file> [--jumlah 20]` | Cek daftar proxy dari file |
| `proxyz gateway [--port 8888] [--profil scraper\|cepat\|hemat] [--socks 1080]` | Gateway rotating (HTTP + SOCKS5 opsional) |
| `proxyz warp [--jumlah 1]` | Buat profil WARP WireGuard (`.conf`, mode 0600) |
| `proxyz residential [--api-key KEY \| --signup]` | Proxy residential Webshare (API resmi) |
| `proxyz sources` | Tabel kesehatan tiap sumber panen |
| `proxyz bench [--jumlah 10]` | Ranking kecepatan unduh tiap proxy HTTP |
| `proxyz test [--port 8888]` | Leak test: IP asli vs IP via gateway |
| `proxyz laporan` | Ringkasan pool ke `output/laporan.md` |
| `proxyz sync-9router [--db PATH] [--ganti]` | Sinkronkan pool ke DB SQLite 9Router |
| `proxyz blacklist add\|remove\|list [entri]` | Kelola proxy yang tidak boleh dipakai |
| `proxyz auto [--interval 60] [--sekali]` | Panen + cek + ekspor berkala |
| `proxyz install-service [--port 8888]` | Buat file service (systemd + Windows Task) |
| `proxyz update [--yes]` | Cek rilis terbaru, update via pip |
| `proxyz doctor [--no-gateway]` | Diagnosa instalasi (config, sumber, pool, gateway) |

## Gateway

Gateway dengerin di `127.0.0.1:8888`. Sengaja localhost doang.
Kalau mau diakses dari HP atau komputer lain, pasang reverse proxy
sendiri dan nyalain token.

Pakainya gampang: set proxy di browser/aplikasi ke
`http://127.0.0.1:8888`, atau SOCKS5 di port yang dikasih `--socks`.
Rotasi jalan sendiri (round-robin), residential diprioritaskan,
dan proxy mati dibuang otomatis sama healer tiap 90 detik.

Buat yang butuh sesi nempel di satu proxy, kirim header
`X-Session-ID: <id>` — proxy-nya dikunci 10 menit. Buat routing
per negara, header `X-Country: ID`.

| Endpoint | Buat apa |
|---|---|
| `GET /api/status` | Statistik pool & gateway |
| `GET /api/proxies` | Daftar proxy di pool |
| `GET /api/random` | Satu proxy acak |
| `GET /api/rotate` | Paksa rotasi ke proxy berikut |
| `GET /api/refill` | Isi ulang pool di background |
| `GET /api/leak-test` | IP asli vs IP via gateway (`zero_leak`) |
| `GET /api/bench?jumlah=5` | Ranking kecepatan pool |
| `GET /api/report` | Laporan pool (JSON) |
| `GET /api/clash.yaml` | Langganan Clash live dari pool |
| `GET /metrics` | Metrik Prometheus |
| `GET /proxy.pac` | File PAC buat browser |
| `GET /dashboard` | Dashboard web (tabel pool, leak test, bench) |

Token opsional: isi env `PROXYZ_TOKEN`, terus kirim
`Authorization: Bearer <token>` atau header `X-Proxyz-Token`.
API dibatasi 60 request/menit per IP. Aktivitas rotate/refill/healer
dicatat di `output/gateway-audit.jsonl`.

## Residential

Butuh IP rumahan? Jalur resminya gini:

```bash
python -m proxyz residential --signup   # buka browser, isi captcha sendiri sekali,
                                        # tempel API key -> divalidasi live
python -m proxyz residential --api-key KUNCIMU   # tambah akun lain
```

Webshare ngasih 10 IP gratis per akun, dan multi-akun didukung —
semua key digabung ke satu pool. Atau tempel proxy manual
(`proto://user:pass@ip:port`) ke `output/proxy_manual.txt`,
gateway ikut makainya.

Kenapa daftarnya manual? Karena akun yang dibikin bot (captcha
dipecah otomatis) cepet di-ban. Daftar sekali, 30 detik, key-nya
dipakai selamanya sama Proxyz.

## Config

Semua setting ada di `config/proxyz.json`. Token jangan ditulis
di file itu — pakai env `PROXYZ_TOKEN`.

```json
{"gateway_port": 8888, "healer_interval": 90, "min_healthy": 5,
 "healer_target": 10, "check_timeout": 5.0, "check_workers": 100,
 "check_target": 20, "max_latency_ms": 1200, "session_ttl": 600,
 "rate_limit_per_min": 60, "audit_log": true,
 "schedule_interval_min": 60, "schedule_target": 20}
```

Profil gateway (`--profil`): `scraper` (rotasi agresif, pool 30),
`cepat` (cuma proxy ≤350 ms), `hemat` (pool kecil, sesi 30 menit).

## Sering ditanya

**Ini legal nggak?**
Tool-nya legal — cuma pakai sumber proxy publik sama API resmi
(Webshare, Cloudflare). Yang jadi tanggung jawab kamu: jangan kirim
data sensitif lewat proxy publik yang nggak kamu kenal, dan patuhi
ToS layanan yang kamu pakai.

**Kenapa `panen` dapat 0 proxy hidup?**
Coba lagi nanti, ganti jaringan, atau pakai `--negara` lain.
Jalankan `proxyz doctor` buat mastiin instalasi kamu sehat.

**Bisa jalan di Windows?**
Bisa. Python 3.9 ke atas, semua perintah sama. Buat auto-jalan
pas login, pakai `proxyz install-service` (bikin Task Scheduler).

**API key Webshare gue disimpen di mana?**
Di `config/webshare.json` lokal (mode 0600), nggak pernah di-commit.
Kalau key bocor, hapus file itu terus bikin key baru di dashboard
Webshare.

## Kalau error

| Gejala | Biasanya kenapa |
|---|---|
| `pool kosong — panen dulu` | Jalankan `proxyz panen` dulu, atau biarin gateway panen sendiri pas start |
| `502` pas browsing lewat gateway | Semua proxy di pool mati — healer bakal isi ulang, atau `proxyz panen` ulang |
| `401 token dibutuhkan` | Isi `PROXYZ_TOKEN` di env, kirim `Authorization: Bearer <token>` |
| `429 rate limit` | Tunggu sekitar 1 menit, atau naikin `rate_limit_per_min` di config |
| `proxyz update` 404 | Belum ada Release di GitHub — updater otomatis fallback ke tags |
| Gateway nggak bisa diakses | Cek ada proses lain di port 8888 nggak; jalankan `proxyz doctor` |
| `0 hidup` terus-menerus | Jaringan ngeblok TCP langsung ke proxy (misalnya sandbox) — coba di laptop/PC biasa |

Masih buntu? Jalankan `proxyz doctor` dan sertain output-nya pas
buka issue.

## Rencana ke depan

- IPv6 buat checker & gateway
- `proxyz serve` — gateway + auto dalam satu proses
- Ekspor Surge / Shadowrocket
- Dashboard v3 — grafik latensi & riwayat pool
- Hapus shim `proxyx` di v3.0.0

Punya ide lain? Buka [issue fitur](.github/ISSUE_TEMPLATE/feature_request.md).

## Ngembangin

```bash
git clone https://github.com/Dvifnyz/Proxyz.git
cd Proxyz
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q            # 83 tes, semuanya hijau
python -m proxyz doctor
```

Panduan kontribusi ada di [CONTRIBUTING.md](CONTRIBUTING.md).
API Python-nya di [docs/API.md](docs/API.md), arsitektur di
[docs/ARSITEKTUR.md](docs/ARSITEKTUR.md).

## Keamanan

Nemu celah? Jangan buka issue publik — baca
[SECURITY.md](SECURITY.md) dulu. Singkatnya: gateway cuma bind
localhost, token nggak pernah ditulis ke file config, API key
Webshare disimpen lokal mode 0600, dan updater nggak pernah
ngejalanin perintah dari server.

## Terima kasih

Makasih buat
[itzluthfi](https://github.com/itzluthfi) yang repo
[petani-proxy](https://github.com/itzluthfi/petani-proxy)-nya jadi
bahan bedah tool ini.

Lisensi [MIT](LICENSE).
