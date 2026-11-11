# ⚡ Proxyz

[![Release](https://img.shields.io/github/v/release/Dvifnyz/Proxyz)](https://github.com/Dvifnyz/Proxyz/releases)
[![CI](https://github.com/Dvifnyz/Proxyz/actions/workflows/ci.yml/badge.svg)](https://github.com/Dvifnyz/Proxyz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/Dvifnyz/Proxyz)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-79%20passed-brightgreen)](#pengembangan)

**Proxyz** adalah toolkit proxy open-source: panen proxy publik dari
35 sumber, cek mana yang benar-benar hidup (anonimitas, latensi,
negara), lalu sajikan lewat gateway lokal berputar — lengkap dengan
WARP, proxy residential, dan sinkronisasi ke 9Router.

Dibangun dari bedah penuh
[itzluthfi/petani-proxy](https://github.com/itzluthfi/petani-proxy)
(~8.682 baris): semua fitur sahnya di-port dan diperbaiki, tanpa
membawa cacat keamanannya (lihat [tabel port](#port-dari-petani-proxy)).

> **Nama baru di v3.0.0:** tool ini sebelumnya bernama **Proxyx**.
> Perintah `proxyx` dan `import proxyx` masih jalan sampai v4.0.0,
> tapi sudah deprecated — pakai `proxyz`. Panduan migrasi:
> [docs/MIGRASI-3.0.md](docs/MIGRASI-3.0.md).

## Daftar isi

- [Kenapa Proxyz?](#kenapa-proxyz)
- [Mulai cepat](#mulai-cepat)
- [Perintah](#perintah)
- [Gateway & API](#gateway--api)
- [Proxy residential](#proxy-residential)
- [Konfigurasi](#konfigurasi)
- [API Python](#api-python)
- [Port dari petani-proxy](#port-dari-petani-proxy)
- [Pengembangan](#pengembangan)
- [Keamanan](#keamanan)
- [Lisensi & ucapan terima kasih](#lisensi--ucapan-terima-kasih)

## Kenapa Proxyz?

| Masalah di repo asli | Yang Proxyz lakukan |
|---|---|
| 3 checker yang saling duplikat | 1 pipeline async (aiohttp + fallback urllib) |
| TLS dimatikan (`verify=False`) | Verifikasi TLS tetap nyala (system CA store) |
| API gateway tanpa auth, CORS `*` | Token opsional + rate limit + audit log |
| Updater menjalankan perintah remote via `shell=True` | Update via `pip` dari release GitHub |
| Docker CMD memakai flag yang tidak ada | CMD memakai perintah CLI yang benar-benar ada |
| Sinkronisasi 9Router menghapus baris orang lain | Insert-only + backup + dedup |
| Filter negara hanya jalan di 1 sumber | Filter negara di semua sumber + routing per negara |
| Variabel `.env` tidak dibaca kode mana pun | `config/proxyz.json` benar-benar dibaca |

## Mulai cepat

**Syarat:** Python 3.9+.

```bash
git clone https://github.com/Dvifnyz/Proxyz.git
cd Proxyz
pip install -e .            # atau: pip install -r requirements.txt

python -m proxyz panen --jumlah 20     # panen + cek 20 proxy hidup
python -m proxyz gateway               # gateway di http://127.0.0.1:8888
curl -x http://127.0.0.1:8888 http://api.ipify.org
```

Tanpa argumen, `python -m proxyz` membuka menu interaktif.

## Perintah

| Perintah | Fungsi |
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

Contoh alur lengkap:

```bash
python -m proxyz panen --jumlah 20 --negara ID --tier cepat
python -m proxyz bench --jumlah 10
python -m proxyz gateway --profil cepat
python -m proxyz test
```

## Gateway & API

Gateway mendengarkan di `127.0.0.1:8888` (localhost saja — sengaja
tidak di-expose ke LAN). Pakai di browser/aplikasi lewat
`http://127.0.0.1:8888` sebagai proxy, atau lewat SOCKS5 di port yang
ditentukan `--socks`.

| Endpoint | Fungsi |
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
| `GET /proxy.pac` | File PAC untuk browser |
| `GET /dashboard` | Dashboard web (tabel pool, leak test, bench) |

**Autentikasi (opsional):** isi env `PROXYZ_TOKEN`, lalu kirim
`Authorization: Bearer <token>` (atau header `X-Proxyz-Token`).
API dibatasi 60 request/menit per IP (bisa diubah di config);
aktivitas `rotate`/`refill`/healer tercatat di
`output/gateway-audit.jsonl`.

**Sticky session:** kirim header `X-Session-ID: <id>` untuk memakai
proxy yang sama selama 10 menit (bisa diubah: `session_ttl`).
**Routing negara:** header `X-Country: ID`.

## Proxy residential

Butuh IP rumahan (residential)? Jalur resminya:

```bash
python -m proxyz residential --signup   # buka browser + siapkan password;
                                        # isi captcha sendiri sekali,
                                        # tempel API key -> divalidasi live
python -m proxyz residential --api-key KUNCIMU   # tambah akun lain
```

Multi-akun didukung — semua key digabung ke satu pool. Atau tempel
proxy manual (`proto://user:pass@ip:port`) ke
`output/proxy_manual.txt`; gateway ikut memakainya dan residential
diprioritaskan di pool.

> Proxyz **tidak** menyediakan pemecah captcha otomatis, farm akun
> massal, atau bypass anti-bot. Akun hasil farm cepat di-banned dan
> IP-nya mati — itu yang membuat tool berumur pendek.

## Konfigurasi

Semua setting di `config/proxyz.json` (ditambah env bila ada).
Token **jangan** ditulis di file ini — pakai env `PROXYZ_TOKEN`.

```json
{"gateway_port": 8888, "healer_interval": 90, "min_healthy": 5,
 "healer_target": 10, "check_timeout": 5.0, "check_workers": 100,
 "check_target": 20, "max_latency_ms": 1200, "session_ttl": 600,
 "rate_limit_per_min": 60, "audit_log": true,
 "schedule_interval_min": 60, "schedule_target": 20}
```

Profil gateway (`--profil`): `scraper` (rotasi agresif, pool 30),
`cepat` (hanya proxy ≤350 ms), `hemat` (pool kecil, sesi 30 menit).

## API Python

API publik stabil sejak v2.0.0, didokumentasikan di
[docs/API.md](docs/API.md):

```python
from proxyz.harvester import harvest
from proxyz.checker import check_pool_sync
from proxyz.gateway import serve
from proxyz.pool import Pool

hidup = check_pool_sync(harvest(country="ID"), target=20)
serve(Pool(hidup), port=8888)
```

## Port dari petani-proxy

| Fitur asli | Status di Proxyz |
|---|---|
| Fast async harvester (30 sumber) | ✅ 35 sumber + skor kesehatan + backoff |
| Checker (anonimitas, latensi, GeoIP) | ✅ + GeoIP batch + SOCKS handshake sendiri |
| Gateway rotating + dashboard + REST + PAC | ✅ + healer probe HTTP + token + leak test + bench |
| WARP (WireGuard) | ✅ via API resmi Cloudflare |
| Ekspor TXT/JSON/CSV/Clash | ✅ + penulisan atomik + backup otomatis |
| Residential Webshare | ✅ via API resmi (multi-akun) + signup semi-otomatis |
| Sinkronisasi 9Router (SQLite) | ✅ aman: insert-only, backup dulu, dedup |
| Profil (scraper / cepat / hemat) | ✅ benar-benar mengubah perilaku gateway |
| Updater otomatis | ✅ diganti updater aman (pip, tanpa perintah remote) |
| Webshare Hunter (bikin akun otomatis + solver captcha audio) | ❌ tidak dibuat — akun hasil farm cepat di-banned, IP mati |
| Grok Farm (bikin akun Grok otomatis via email sekali pakai + OTP) | ❌ tidak dibuat — alasan yang sama |
| Kredensial Gmail hardcode di grok_farm | ❌ tidak pernah disalin |

Studi lengkapnya: [docs/STUDI_PETANI_PROXY.md](docs/STUDI_PETANI_PROXY.md).

## Pengembangan

```bash
git clone https://github.com/Dvifnyz/Proxyz.git
cd Proxyz
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q            # 79 tes
python -m proxyz doctor
```

Lihat [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan kontribusi
(gaya commit, cara menambah sumber, cara menambah perintah).

## Keamanan

Jangan laporkan kerentanan lewat issue publik — baca
[SECURITY.md](SECURITY.md). Ringkasnya: gateway hanya bind localhost,
token tidak pernah ditulis ke file config, API key Webshare disimpan
lokal mode 0600, dan updater tidak pernah menjalankan perintah dari
server.

## Lisensi & ucapan terima kasih

Lisensi [MIT](LICENSE).

Terima kasih kepada
[itzluthfi](https://github.com/itzluthfi) — pembuat
[petani-proxy](https://github.com/itzluthfi/petani-proxy) yang
menjadi bahan studi dan inspirasi tool ini.
