# Proxyx API — Stabil sejak v2.0.0

Fungsi-fungsi di bawah ini adalah API publik Proxyx. Sejak v2.0.0
tandatangan dan perilaku dasarnya DIJAMIN stabil antar rilis minor
(2.x). Perubahan yang merusak hanya terjadi di rilis mayor berikutnya.

## Panen & cek

```python
from proxyx.harvester import harvest, build_jobs, health_report
from proxyx.checker import check_pool_sync, check_one, enrich_geo

kandidat = harvest(protocols=["http"], country="ID")  # list[dict]
hidup = check_pool_sync(kandidat, target=20)          # list[Proxy]
```

- `harvest()` mengembalikan kandidat (dict `protocol/ip/port/source`),
  sudah difilter blacklist.
- `check_pool_sync(cands, target=N)` mengembalikan `list[Proxy]` hidup,
  diurutkan skor tertinggi dulu.

## Model & pool

```python
from proxyx.models import Proxy
from proxyx.pool import Pool

p = Proxy(protocol="http", ip="1.2.3.4", port=8080)
pool = Pool([p], session_ttl=600)
nxt = pool.next()                       # rotasi round-robin
nxt = pool.next(session_id="s1")        # sticky session
pool.mark_success(p) / pool.mark_failed(p)
pool.prune(["1.2.3.4:8080"])
```

## Gateway

```python
from proxyx.gateway import serve, load_pool_from_disk, make_handler

pool = Pool(load_pool_from_disk())
serve(pool, port=8888, token="", refill_fn=None,
      healer=True, healer_interval=90,
      rate_limit_per_min=60, audit_path=None, socks_port=0)
```

Endpoint REST: `/api/status`, `/api/proxies`, `/api/random`,
`/api/rotate`, `/api/refill`, `/api/leak-test`, `/api/bench`,
`/api/report`, `/api/clash.yaml`, `/metrics`, `/proxy.pac`.

## Ekspor, bench, 9Router, laporan

```python
from proxyx.exporter import export_all, export_clash, clash_yaml
from proxyx.bench import bench_pool
from proxyx.router import sync_to_9router, find_9router_db
from proxyx.report import build_report, report_markdown
from proxyx.scheduler import run_cycle, run_scheduler
from proxyx.doctor import run_doctor
```

## Konfigurasi

```python
from proxyx.config import load_config, apply_profile, PROFILES
cfg = load_config()  # default -> config/proxyx.json -> env
cfg = apply_profile(cfg, "cepat")  # scraper | cepat | hemat
```

## Migrasi 2.0.0

- `config/webshare.json` format lama `{"api_key": "..."}` dimigrasi
  otomatis ke `{"api_keys": [...]}` saat pertama dibaca. Tidak ada
  tindakan manual; key tidak berubah.
- `proxyx panen --jumlah` default tetap 20; `gateway --port 0`
  berarti "pakai config".
- Yang TIDAK PERNAH ada dan tetap tidak ada: pemecah captcha
  otomatis, farm akun massal, bypass anti-bot.
