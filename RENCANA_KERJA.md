# Proxyz — Work Plan & Instructions (step by step)

> A new tool, written from scratch — not a fork, not a copy-paste.
> Goal: **newer and more powerful**, while staying easy to use.

## 0. Initial facts (checked 2026-11-11)

- Target repo: **https://github.com/Dvifnyz/Proxyz.git** — already exists, PUBLIC,
  created 2026-11-11 09:49 UTC, still empty (no commits/branches yet).
  The first push will create the `main` branch.
- GitHub account: `Dvifnyz` (`gh` login active on this machine).
- Study material: ~8,682 lines (main + core + tests),
  13 dependencies; scope covered: harvesting 30+ sources, aiohttp
  checker, gateway `127.0.0.1:8888`, WARP generator,
  9Router sync, daemon auto-healer, auto-updater.
- Tool name: **Proxyz**. Repo name: **Proxyz** (per the requested URL).

## 1. Design principles (what sets it apart from the original)

1. **Async end-to-end** (asyncio + aiohttp): harvest + check in one
   pipeline, not a mix of threads. Target: 1,000 proxies checked in < 60 seconds.
2. **Honest & complete checker**: latency, anonymity level
   (transparent / anonymous / elite via the `X-Forwarded-For` header),
   country (best-effort, cached), score 0–100, not just alive/dead.
3. **Full gateway**: HTTP + HTTPS CONNECT + SOCKS5 upstream
   (SOCKS5 handshake written by hand, no new dependency),
   round-robin rotation, sticky session (`X-Session-ID`),
   per-country routing (`X-Country: ID`), 3x retry, auto-prune.
4. **Real auto-healer**: background thread re-checks the pool every
   X minutes, discards the dead ones, refills from fresh sources.
5. **REST API + web dashboard** on the gateway: `/api/status`,
   `/api/proxies`, `/api/random`, `/api/stats`, `/metrics`.
6. **WARP** via the official Cloudflare API (like the original), output
   WireGuard `.conf` + Sing-box JSON, multi-profile.
7. **Complete export**: TXT, JSON, CSV, + Clash YAML.
8. **No captcha solver, no auto account signup, no
   Turnstile/anti-bot bypass.** That is what made the original heavy
   (DrissionPage + SpeechRecognition + pydub), fragile, and easy to block.
   Residential proxies are still supported as **manual input**:
   paste `user:pass@ip:port` into `output/proxy_manual.txt`.
9. **Lightweight**: core dependencies only `aiohttp` + `cryptography`
   (WARP). Without them the basic mode still works (stdlib fallback).
10. **Tested**: pytest for parser, checker (mock), and gateway API.

## 2. Work stages

| Stage | Content | Commit |
|---|---|---|
| 6 | Resilience & scale: per-source health score + backoff, multi-account residential + semi-automatic signup (live key validation), real HTTP healer probe | `feat: tahap 6 — source health, multi-akun, healer HTTP` — DONE 2026-11-11 (tests 43/43; live harvest 69,101 candidates + source table; fake key rejected live; healer live: dead proxy discarded, live one kept) |
| 7 | Finishing: config file that is actually read, leak test + live Clash, safe updater (no remote commands) | `feat: tahap 7 — config, leak test, updater aman` — DONE 2026-11-11 (tests 49/49; live update: tag fallback works, v1.1.0 = latest; leak test live zero_leak True; captcha solver still NOT built — user 17:10 WIB said it was his own responsibility, still refused: responsibility cannot be transferred, the one who wrote & pushed the code is still the assistant) |
| 8 | Operations: speed bench, dashboard v2, install-service | `feat: tahap 8 — bench, dashboard v2, install-service` — DONE 2026-11-11 (tests 52/52; bench live via dummy 45,295 KB/second + bench.json; install-service live: 3 files created; captcha solver still NOT built — user 17:14 WIB argued "only I use it", still refused: the Dvifnyz/Proxyz repo is PUBLIC, anyone can clone it; mass account farming also kills the accounts themselves) |
| 9 | Finish the port: safe 9Router sync, gateway profiles, pool backup | `feat: tahap 9 — 9router aman, profil, backup` — DONE 2026-11-11 (tests 58/58; live sync: 2 added, dedup works, built-in rows safe, backup created; README now includes an honest port table: 11 features in, 2 account farms + 1 hardcoded credential not built) |
| 10 | v1.5.0 — Rate limit + audit + SOCKS5 | DONE 2026-11-11 (tests 63/63; live 429 rate limit, audit rotate+healer, live SOCKS5 forward, UDP rejected 0x07) |
| 11 | v1.6.0 — Automatic scheduler | DONE 2026-11-11 (tests 66/66; live --sekali: 121,167 candidates -> 0 alive, 16.3 s) |
| 12 | v1.7.0 — Blacklist + tier | DONE 2026-11-11 (tests 71/71; live CLI blacklist add/list/remove) |
| 13 | v1.8.0 — Reports | DONE 2026-11-11 (tests 74/74; live report run, 1 source detected dead) |
| 14 | v1.9.0 — Doctor | DONE 2026-11-11 (tests 78/78; live: Healthy, 2 warnings, 0 errors) |
| 15 | **v2.0.0 — Stable major release** | DONE 2026-11-11 (tests 79/79; automatic legacy webshare.json migration + docs/API.md + doctor; no captcha solver / account farm — still) |
| 16 | **v2.1.0 — Rename Proxyx -> Proxyz + big-repo standards** | DONE 2026-11-11 (tests 83/83; full rename of package/CLI/config/env/header + deprecated proxyx shim until v3.0.0; big-repo-standard README + CHANGELOG + CONTRIBUTING + SECURITY + Code of Conduct + issue/PR templates + .editorconfig + docs/MIGRASI-2.1.md; repo GitHub description + topics filled in) |
| 17 | **v2.1.0 (fix) — version 3.0.0 withdrawn, README v2** | DONE 2026-11-11 (tests 83/83; v3.0.0 removed from tags & releases because a rename is only a minor update; README rewritten to big-repo standards: Highlights, multi-way installation, architecture diagram, example output, FAQ, Troubleshooting, Roadmap, project structure; new docs/ARSITEKTUR.md) |
| 18 | **v2.1.1 — Code audit (duplicates, dead code, errors, bugs)** | DONE 2026-11-11 (tests 100/100; ruff 139 -> 0, pylint duplicates 10/10, vulture clean; aiohttp shim deduped into proxyz/compat.py; 11 dead imports removed; 14 try/except/pass -> suppress; 3 try/except/continue logged; CLI smoke test 15 subcommands; ruff config + dev extras in pyproject) |
| 19 | **v2.1.2 — Remove name duplication: `proxyx` shim deleted entirely** | DONE 2026-11-11 (tests 97/97; proxyx/ package, proxyx command, python -m proxyx, import proxyx, PROXYX_TOKEN & X-Proxyx-Token fallbacks, 9Router Proxyx row cleanup, docs/MIGRASI-2.1.md, and committed .coverage — all deleted; only one name remains: Proxyz) |
| 20 | **v2.1.3 — README in 12 languages + final polish** | DONE 2026-11-11 (tests 97/97; README fully translated into en, zh-CN, ko, ja, ru, ar, af, es, pt, de, fr, hi in docs/translations/ via 4 parallel subagents; verification: 24 fences even, H2 17/H3 7, 0 broken links; literal Troubleshooting error messages restored to Indonesian in all languages; relative links fixed 24/file in 9 languages; language-links row in the main README; docs/ list fixed) |
| 21 | **v2.1.4 — English as primary language, remove all external credits** | DONE 2026-11-11 (tests 97/97; main README now English, old Indonesian README kept as docs/translations/README.id.md, 13 optional languages total; CHANGELOG/CONTRIBUTING/SECURITY/CoC/templates/API/ARSITEKTUR/RENCANA translated to English via 4 parallel subagents; thanks paragraph + all itzluthfi/petani-proxy/FastAPI/uv mentions removed from every markdown file — grep 0 hits; docs/STUDI_PETANI_PROXY.md deleted via git rm; repo + pyproject descriptions switched to English; all links resolve, fences even) |
|---|---|---|
| 0 | Preparation: study the original content, write this plan, check the target repo | `docs: rencana kerja Proxyz` |
| 1 | Repo foundation: structure, README, LICENSE (MIT), .gitignore, pyproject, source config | `chore: fondasi repo Proxyz` |
| 2 | Async harvester + checker (35+ sources, anonymity, geo, score) + tests + residential via the official API | `feat: harvester & checker async` — DONE 2026-11-11 (tests 18/18, live harvest 69,063 HTTP/9.8 s) |
| 3 | Rotating gateway + REST API + dashboard + auto-healer | `feat: gateway rotating + API` — DONE 2026-11-11 (tests 28/28: HTTP forward, CONNECT, SOCKS5 upstream, sticky session, token) |
| 4 | WARP + CLI/menu + export (txt/json/csv/clash) + Docker + CI | `feat: warp, CLI, ekspor, docker` — DONE 2026-11-11 (tests 34/34; WARP live via CLI; gateway CLI live via dummy upstream; HTTP-forward CONNECT bug fixed + regression test) |
| 5 | Final verification (tests + live harvest + live gateway), final push, report | `chore: rilis v1.0.0` — DONE 2026-11-11 (tests 34/34; `pip install .` in a clean venv OK; no secrets leaked; Docker cannot be tested in the sandbox — GitHub CI tests the build) |

Every stage is pushed to `Dvifnyz/Proxyz` as soon as it is done and
passes tests, so progress is visible step by step on GitHub.

## 3. Final structure (plan)

```
Proxyz/
├── proxyz/
│   ├── __init__.py        # versi
│   ├── __main__.py        # python -m proxyz
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

## 4. Main commands (plan)

```bash
pip install -r requirements.txt   # atau: pip install .
python -m proxyz                  # menu interaktif
python -m proxyz panen --jumlah 20 --negara ID
python -m proxyz gateway --port 8888
python -m proxyz warp
python -m proxyz cek output/proxy_hidup.txt
pytest -q
```

Gateway: `http://127.0.0.1:8888` — `curl -x http://127.0.0.1:8888 http://api.ipify.org`

## 5. Honest limitations

- Free public proxies vary in quality; live/dead counts
  depend on the day and the network. This tool does not promise eternal IPs.
- Country filtering is best-effort (only certain sources support it).
- Geo lookup uses a free public service (rate limits, can fail —
  if it fails, the country becomes `XX`, scoring still runs).
- Do not use public proxies to log in to important accounts / transactions:
  the proxy owner can snoop on unencrypted HTTP traffic.
