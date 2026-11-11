# Proxyx — Rencana & Instruksi Kerja (bertahap)

> Tool baru, ditulis dari nol, terinspirasi PetaniProxy
> (`itzluthfi/petani-proxy`, MIT, v1.2.0) — bukan fork, bukan copy-paste.
> Target: **lebih baru dan lebih powerful**, tapi tetap gampang dipakai.

## 0. Fakta awal (dicek 2026-11-11)

- Repo tujuan: **https://github.com/Dvifnyz/Proxyz.git** — sudah ada, PUBLIC,
  dibuat 2026-11-11 09:49 UTC, masih kosong (belum ada commit/branch).
  Push pertama akan membuat branch `main`.
- Akun GitHub: `Dvifnyz` (login `gh` aktif di mesin ini).
- Referensi: `itzluthfi/petani-proxy`, ~8.682 baris (main + core + tests),
  13 dependency, fitur: panen 30+ sumber, checker aiohttp, gateway
  `127.0.0.1:8888`, WARP generator, Webshare Hunter (audio captcha solver),
  CapSolver opsional, sync 9Router, daemon auto-healer, auto-updater.
- Nama tool: **Proxyx**. Nama repo: **Proxyz** (sesuai URL yang diminta).

## 1. Prinsip desain (yang membedakan dari aslinya)

1. **Async end-to-end** (asyncio + aiohttp): panen + cek dalam satu
   pipeline, bukan thread campur aduk. Target: 1.000 proxy dicek < 60 detik.
2. **Checker jujur & lengkap**: latency, level anonimitas
   (transparent / anonymous / elite via header `X-Forwarded-For`),
   negara (best-effort, cache), skor 0–100, bukan sekadar hidup/mati.
3. **Gateway full**: HTTP + HTTPS CONNECT + SOCKS5 upstream
   (handshake SOCKS5 ditulis sendiri, tanpa dependency baru),
   rotasi round-robin, sticky session (`X-Session-ID`),
   routing per negara (`X-Country: ID`), retry 3x, auto-prune.
4. **Auto-healer beneran**: background thread cek ulang pool tiap
   X menit, buang yang mati, isi ulang dari sumber segar.
5. **REST API + dashboard web** di gateway: `/api/status`,
   `/api/proxies`, `/api/random`, `/api/stats`, `/metrics`.
6. **WARP** via API resmi Cloudflare (seperti aslinya), output
   WireGuard `.conf` + Sing-box JSON, multi-profil.
7. **Ekspor lengkap**: TXT, JSON, CSV, + Clash YAML.
8. **Tanpa pemecah captcha, tanpa auto-daftar akun, tanpa bypass
   Turnstile/anti-bot.** Itu yang bikin aslinya berat (DrissionPage +
   SpeechRecognition + pydub), rapuh, dan gampang diblokir.
   Proxy residential tetap didukung sebagai **input manual**:
   tempel `user:pass@ip:port` ke `output/proxy_manual.txt`.
9. **Ringan**: dependency inti cuma `aiohttp` + `cryptography`
   (WARP). Tanpa itu pun mode dasar tetap jalan (fallback stdlib).
10. **Teruji**: pytest untuk parser, checker (mock), dan API gateway.

## 2. Tahapan kerja

| Tahap | Isi | Commit |
|---|---|---|
| 6 | Ketahanan & skala: skor kesehatan sumber + backoff, residential multi-akun + signup semi-otomatis (validasi key live), healer probe HTTP beneran | `feat: tahap 6 — source health, multi-akun, healer HTTP` — SELESAI 2026-11-11 (tes 43/43; panen live 69.101 kandidat + tabel sumber; key palsu ditolak live; healer live: proxy mati dibuang, yang hidup dipertahankan) |
| 7 | Finishing: config file yang benar-benar dibaca, leak test + Clash live, updater aman (tanpa perintah remote) | `feat: tahap 7 — config, leak test, updater aman` — SELESAI 2026-11-11 (tes 49/49; update live: fallback tag jalan, v1.1.0 = terbaru; leak test live zero_leak True; captcha solver tetap TIDAK dibuat — user 17:10 WIB mengaku tanggung jawab sendiri, tetap ditolak: tanggung jawab tidak bisa dipindah, yang nulis & nge-push kodenya tetap asisten) |
|---|---|---|
| 0 | Persiapan: pelajari isi asli, tulis rencana ini, cek repo tujuan | `docs: rencana kerja Proxyx` |
| 1 | Fondasi repo: struktur, README, LICENSE (MIT), .gitignore, pyproject, config sumber | `chore: fondasi repo Proxyx` |
| 2 | Harvester + checker async (sumber 35+, anonimitas, geo, skor) + tes + residential via API resmi | `feat: harvester & checker async` — SELESAI 2026-11-11 (tes 18/18, panen live 69.063 HTTP/9,8 dtk) |
| 3 | Gateway rotating + REST API + dashboard + auto-healer | `feat: gateway rotating + API` — SELESAI 2026-11-11 (tes 28/28: forward HTTP, CONNECT, SOCKS5 upstream, sticky session, token) |
| 4 | WARP + CLI/menu + ekspor (txt/json/csv/clash) + Docker + CI | `feat: warp, CLI, ekspor, docker` — SELESAI 2026-11-11 (tes 34/34; WARP live via CLI; gateway CLI live via dummy upstream; bug forward-HTTP CONNECT diperbaiki + tes regresi) |
| 5 | Verifikasi akhir (tes + panen live + gateway live), push final, laporan | `chore: rilis v1.0.0` — SELESAI 2026-11-11 (tes 34/34; `pip install .` di venv bersih OK; tidak ada rahasia bocor; Docker tidak bisa dites di sandbox — CI GitHub yang menguji build-nya) |

Setiap tahap di-push ke `Dvifnyz/Proxyz` begitu selesai dan lolos tes,
jadi progresnya kelihatan bertahap di GitHub.

## 3. Struktur akhir (rencana)

```
Proxyx/
├── proxyx/
│   ├── __init__.py        # versi
│   ├── __main__.py        # python -m proxyx
│   ├── sources.py         # daftar sumber proxy publik
│   ├── harvester.py       # panen async dari semua sumber
│   ├── checker.py         # cek hidup + anonimitas + geo + skor
│   ├── pool.py            # pool + rotasi + sticky session + healer
│   ├── gateway.py         # gateway HTTP/CONNECT/SOCKS5 + REST API + dashboard
│   ├── warp.py            # generator WARP (API resmi Cloudflare)
│   ├── exporter.py        # ekspor txt/json/csv/clash
│   └── cli.py             # menu interaktif + argumen CLI
├── config/
│   └── sources.json       # sumber proxy (bisa diedit user)
├── tests/
│   ├── test_parser.py
│   ├── test_checker.py
│   └── test_gateway.py
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml
├── pyproject.toml
├── requirements.txt
├── README.md
├── RENCANA_KERJA.md       # file ini
└── LICENSE
```

## 4. Perintah utama (rencana)

```bash
pip install -r requirements.txt   # atau: pip install .
python -m proxyx                  # menu interaktif
python -m proxyx panen --jumlah 20 --negara ID
python -m proxyx gateway --port 8888
python -m proxyx warp
python -m proxyx cek output/proxy_hidup.txt
pytest -q
```

Gateway: `http://127.0.0.1:8888` — `curl -x http://127.0.0.1:8888 http://api.ipify.org`

## 5. Batasan jujur

- Proxy publik gratis kualitasnya berubah-ubah; angka hidup/mati
  tergantung hari dan jaringan. Tool ini tidak menjanjikan IP abadi.
- Filter negara best-effort (hanya sumber tertentu yang mendukung).
- Geo lookup memakai layanan publik gratis (rate limit, bisa gagal —
  kalau gagal, negara jadi `XX`, skor tetap jalan).
- Jangan pakai proxy publik untuk login akun penting / transaksi:
  pemilik proxy bisa mengintip traffic HTTP tak terenkripsi.
