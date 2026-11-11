# Proxyz API — Stable since v2.0.0

The functions below are Proxyz's public API. Since v2.0.0
their signatures and basic behavior are GUARANTEED stable across
minor releases (2.x). Breaking changes only happen in the next
major release.

## Harvest & check

```python
from proxyz.harvester import harvest, build_jobs, health_report
from proxyz.checker import check_pool_sync, check_one, enrich_geo

kandidat = harvest(protocols=["http"], country="ID")  # list[dict]
hidup = check_pool_sync(kandidat, target=20)          # list[Proxy]
```

- `harvest()` returns candidates (dict `protocol/ip/port/source`),
  already blacklist-filtered.
- `check_pool_sync(cands, target=N)` returns a `list[Proxy]` of live
  proxies, sorted by highest score first.

## Model & pool

```python
from proxyz.models import Proxy
from proxyz.pool import Pool

p = Proxy(protocol="http", ip="1.2.3.4", port=8080)
pool = Pool([p], session_ttl=600)
nxt = pool.next()                       # rotasi round-robin
nxt = pool.next(session_id="s1")        # sticky session
pool.mark_success(p) / pool.mark_failed(p)
pool.prune(["1.2.3.4:8080"])
```

## Gateway

```python
from proxyz.gateway import serve, load_pool_from_disk, make_handler

pool = Pool(load_pool_from_disk())
serve(pool, port=8888, token="", refill_fn=None,
      healer=True, healer_interval=90,
      rate_limit_per_min=60, audit_path=None, socks_port=0)
```

REST endpoints: `/api/status`, `/api/proxies`, `/api/random`,
`/api/rotate`, `/api/refill`, `/api/leak-test`, `/api/bench`,
`/api/report`, `/api/clash.yaml`, `/metrics`, `/proxy.pac`.

## Export, bench, 9Router, report

```python
from proxyz.exporter import export_all, export_clash, clash_yaml
from proxyz.bench import bench_pool
from proxyz.router import sync_to_9router, find_9router_db
from proxyz.report import build_report, report_markdown
from proxyz.scheduler import run_cycle, run_scheduler
from proxyz.doctor import run_doctor
```

## Configuration

```python
from proxyz.config import load_config, apply_profile, PROFILES
cfg = load_config()  # default -> config/proxyz.json -> env
cfg = apply_profile(cfg, "cepat")  # scraper | cepat | hemat
```

## Migration 2.0.0

- The old `config/webshare.json` format `{"api_key": "..."}` is
  migrated automatically to `{"api_keys": [...]}` on first read. No
  manual action; the key does not change.
- `proxyz panen --jumlah` default stays 20; `gateway --port 0`
  means "use config".
- What NEVER existed and still does not: automatic captcha
  solver, mass account farm, anti-bot bypass.
