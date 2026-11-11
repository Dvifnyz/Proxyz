# ⚡ Proxyx

**Panen proxy gratis → cek → gateway lokal berputar → WARP. Lebih cepat dan lebih lengkap dari pendahulunya, tetap gampang dipakai.**

Proxyx ditulis dari nol (bukan fork), terinspirasi
[PetaniProxy](https://github.com/itzluthfi/petani-proxy) (`itzluthfi/petani-proxy`, MIT).
Ia mengambil ide intinya — panen sumber publik, cek, gateway lokal, WARP —
lalu membangunnya ulang dengan mesin async, checker yang mengukur anonimitas
dan skor, gateway yang mendukung SOCKS5 upstream, dan auto-healer.

> Status: ✅ **v1.4.0 rilis** — Tahap 9 selesai, tes 58/58.
> Detail tahapan di [RENCANA_KERJA.md](RENCANA_KERJA.md).

## Port dari petani-proxy — apa yang masuk, apa yang tidak

Proxyx dibangun dari bedah penuh repo
[itzluthfi/petani-proxy](https://github.com/itzluthfi/petani-proxy)
(~8.682 baris). Hampir semua fiturnya masuk — ini daftar jujurnya:

| Fitur asli | Status di Proxyx |
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

## Kenapa Proxyx?

|  | PetaniProxy v1.2.0 | Proxyx v1.0.0 |
|---|---|---|
| Panen | 30+ sumber | 35 sumber, segar didahulukan |
| Cek | hidup/mati, <350 ms | + anonimitas (elite/anon/transparan), geo, skor 0–100 |
| Gateway | HTTP, port 8888 | HTTP + HTTPS CONNECT + SOCKS5 upstream, sticky session, routing per negara |
| Auto-healer | ada | ada, + isi ulang otomatis dari sumber segar |
| API | 3 endpoint | status, proxies, random, stats, metrics |
| Ekspor | txt/json/csv | + Clash YAML |
| Dependency | 13 (termasuk browser automation + speech recognition) | 2 inti (`aiohttp`, `cryptography`) |
| Captcha solver / auto-daftar akun | ada (rapuh, gampang diblokir) | **tidak ada** — residential via input manual |

## Cara pakai

```bash
git clone https://github.com/Dvifnyz/Proxyz.git
cd Proxyz
pip install -r requirements.txt
python -m proxyx
```

Pilih menu, atau langsung lewat CLI:

```bash
python -m proxyx panen --jumlah 20 --negara ID
python -m proxyx gateway --port 8888
python -m proxyx warp
```

Pakai gateway di program lain:

```bash
curl -x http://127.0.0.1:8888 http://api.ipify.org
```

```python
import requests
proxies = {"http": "http://127.0.0.1:8888", "https": "http://127.0.0.1:8888"}
print(requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=10).json())
```

## Konfigurasi

Semua setting dibaca dari `config/proxyx.json` (ditambah env bila ada).
Jangan tulis token di file ini — token lewat env `PROXYX_TOKEN`.

```json
{"gateway_port": 8888, "healer_interval": 90, "min_healthy": 5,
 "check_timeout": 5.0, "check_workers": 100, "check_target": 20,
 "max_latency_ms": 1200, "session_ttl": 600}
```

## Tes kebocoran & update

```bash
python -m proxyx test              # IP asli vs IP via gateway (zero-leak?)
python -m proxyx update            # cek rilis terbaru, update via pip (aman)
python -m proxyx bench             # ranking kecepatan unduh tiap proxy HTTP
python -m proxyx install-service   # gateway auto-jalan saat mesin nyala
curl http://127.0.0.1:8888/api/leak-test
curl http://127.0.0.1:8888/api/bench?jumlah=5
curl http://127.0.0.1:8888/api/clash.yaml   # langganan Clash live dari pool
```

## Fitur

- 🌾 **Harvester async** — 35 sumber publik (HTTP/SOCKS4/SOCKS5), sumber segar dicek duluan
- 🔍 **Checker** — latency, anonimitas, negara, skor; berhenti otomatis kalau target tercapai
- 🔄 **Gateway rotating** — `127.0.0.1:8888`, round-robin, retry 3x, sticky session, routing negara
- ❤️ **Auto-healer** — buang proxy mati, isi ulang otomatis
- 🌐 **REST API + dashboard** — `/api/status`, `/api/proxies`, `/api/random`, `/api/stats`, `/metrics`
- ☁️ **WARP** — akun Cloudflare WARP resmi → WireGuard `.conf` + Sing-box JSON
- 📦 **Ekspor** — TXT, JSON, CSV, Clash YAML
- 🐳 **Docker** — `docker compose up -d`

## Proxy residential (IP rumahan)

Residential tetap didukung — lewat jalur resmi, bukan farm akun:

1. Jalankan `python -m proxyx residential --signup` — tool membukakan
   halaman daftar + menyiapkan password kuat. Kamu isi form dan captcha
   sendiri sekali (30 detik), lalu tempel API key dari dashboard ke
   terminal — tool memvalidasi key itu **langsung** ke API Webshare
   dan menyimpannya bila valid. Semua langkah lain otomatis.
2. Punya lebih dari satu akun? Ulangi `--signup` / `--api-key` —
   Proxyx memakai **semua** akun (multi-akun, digabung ke satu pool).
   Atau set env: `export WEBSHARE_API_KEY="key1,key2"`.
3. Atau tempel proxy apa pun (`proto://user:pass@ip:port`) ke
   `output/proxy_manual.txt` — gateway ikut memakainya, residential
   diprioritaskan di pool.

**Kenapa tanpa pemecah captcha / auto-daftar akun / bypass Turnstile?**
Karena hasil bedah repo asli menunjukkan cara itu yang bikin akun cepat
di-banned (domain sekali pakai + sidik solver audio terdeteksi) dan hunter
rusak tiap Webshare mengubah halaman — proxy-nya mati dalam hitungan jam.
Jalur API resmi justru yang membuat 10 IP gratis itu tetap hidup.
Detailnya di [proxyx/residential.py](proxyx/residential.py) dan
[docs/STUDI_PETANI_PROXY.md](docs/STUDI_PETANI_PROXY.md).

## Jujur soal gratisan

Proxy publik gratis berubah-ubah: hari ini hidup, besok mati. Panen ulang tiap
mau pakai. Jangan pakai proxy publik untuk login akun penting / transaksi.

## Lisensi

MIT — lihat [LICENSE](LICENSE). Terima kasih kepada `itzluthfi/petani-proxy`
atas ide awalnya.
