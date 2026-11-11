"""Proxyz — harvester: panen proxy publik dari semua sumber, satu pipeline.

Satu mesin panen (bukan tiga seperti repo asli). aiohttp bila tersedia,
fallback urllib ber-thread bila tidak. Verifikasi TLS TETAP NYALA —
repo asli mematikannya (verify=False / ssl=False); kami memakai
system CA store supaya tetap aman dan tetap jalan di mesin biasa.

Tahap 6: tiap sumber punya SKOR KESEHATAN (output/.source_health.json).
Sumber yang gagal 3x beruntun diistirahatkan 1 jam (backoff) supaya
panen tidak buang waktu ke sumber mati — repo asli diam-diam
mengembalikan list kosong dari sumber mati tanpa jejak apa pun.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import ssl
import time
import urllib.request

from .sources import is_fresh_source, load_sources, parse_proxies_from_text, with_country

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Proxyz/1.0"}
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEALTH_FILE = os.path.join(BASE_DIR, "output", ".source_health.json")
SKIP_AFTER_FAILS = 3
SKIP_FOR_SECONDS = 3600


# ------------------------------------------------------------------ kesehatan sumber
def load_health(path: str | None = None) -> dict:
    path = path or HEALTH_FILE
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_health(health: dict, path: str | None = None) -> None:
    path = path or HEALTH_FILE
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(health, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        pass


def should_skip(url: str, health: dict, now: float | None = None) -> bool:
    """True bila sumber gagal >=3x beruntun dan terakhir gagal <1 jam lalu."""
    h = health.get(url)
    if not h:
        return False
    now = now if now is not None else time.time()
    return h.get("fails", 0) >= SKIP_AFTER_FAILS and (now - h.get("last_fail", 0)) < SKIP_FOR_SECONDS


def update_health(health: dict, url: str, ok: bool, count: int,
                  now: float | None = None) -> dict:
    now = now if now is not None else time.time()
    h = health.setdefault(url, {"fails": 0, "yield": 0, "last_ok": 0, "last_fail": 0})
    if ok:
        h["fails"] = 0
        h["last_ok"] = now
        h["yield"] = h.get("yield", 0) + count
    else:
        h["fails"] = h.get("fails", 0) + 1
        h["last_fail"] = now
    return health


def health_report(path: str | None = None) -> list[dict]:
    """Daftar kesehatan sumber, diurutkan dari yang paling produktif."""
    health = load_health(path)
    rows = [{"url": url, **h} for url, h in health.items()]
    rows.sort(key=lambda r: (-r.get("yield", 0), r.get("fails", 0)))
    return rows

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore
    HAS_AIOHTTP = False


def build_jobs(protocols: list[str] | None = None, country: str = "",
               sources_path: str | None = None,
               health: dict | None = None) -> list[tuple[str, str]]:
    """Daftar (url, protokol). Urutan: sumber segar dulu di tiap protokol.
    Sumber yang sedang di-backoff (gagal 3x beruntun) dilewati."""
    sources = load_sources(sources_path)
    health = health if health is not None else load_health()
    if not protocols or "all" in protocols:
        wanted = [p for p in ("http", "socks4", "socks5") if p in sources]
    else:
        wanted = [p.lower() for p in protocols if p.lower() in sources]
    jobs: list[tuple[str, str]] = []
    for proto in wanted:
        urls = sorted(sources.get(proto, []), key=lambda u: (not is_fresh_source(u), u))
        for url in urls:
            # Kunci kesehatan = URL dasar (tanpa query country) supaya
            # pergantian negara tidak mereset riwayat sumber.
            if should_skip(url.split("?")[0], health):
                continue
            jobs.append((with_country(url, country), proto))
    return jobs


def _record_health(jobs, batches: list[tuple[list[dict], bool]]) -> None:
    """Perbarui skor kesehatan dari hasil panen terakhir."""
    health = load_health()
    now = time.time()
    for (url, _proto), (items, ok) in zip(jobs, batches):
        update_health(health, url.split("?")[0], ok, len(items), now)
    save_health(health)


# ------------------------------------------------------------------ aiohttp
async def _fetch_one(session, url: str, protocol: str) -> tuple[list[dict], bool]:
    """Kembalikan (proxy, ok). ok=True bila server menjawab HTTP 200 —
    bedakan 'sumber mati' dari 'sumber hidup tapi kosong'."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
            if r.status != 200:
                return [], False
            text = await r.text(errors="ignore")
    except Exception:
        return [], False
    return parse_proxies_from_text(text, protocol, source=url), True


async def harvest_async(protocols=None, country="", sources_path=None) -> list[dict]:
    jobs = build_jobs(protocols, country, sources_path)
    # System CA store (verifikasi tetap nyala), bukan certifi saja.
    ctx = ssl.create_default_context()
    connector = aiohttp.TCPConnector(ssl=ctx, limit=35)
    # trust_env=True: hormati HTTP(S)_PROXY dari environment (penting di
    # mesin yang internetnya lewat proxy korporat/sandbox; di laptop biasa
    # variabel itu tidak ada, jadi tidak berpengaruh).
    async with aiohttp.ClientSession(headers=UA, connector=connector, trust_env=True) as session:
        results = await asyncio.gather(*[_fetch_one(session, u, p) for u, p in jobs])
    _record_health(jobs, results)
    return _dedup([items for items, _ok in results])


# ------------------------------------------------------------------ fallback
def _fetch_one_urllib(job: tuple[str, str]) -> tuple[list[dict], bool]:
    url, protocol = job
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=12) as r:
            if r.status != 200:
                return [], False
            text = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return [], False
    return parse_proxies_from_text(text, protocol, source=url), True


def harvest_threaded(protocols=None, country="", sources_path=None) -> list[dict]:
    jobs = build_jobs(protocols, country, sources_path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(_fetch_one_urllib, jobs))
    _record_health(jobs, results)
    return _dedup([items for items, _ok in results])


def _dedup(batches: list[list[dict]]) -> list[dict]:
    """Dedup + urutan: yang dari sumber segar didahulukan, sisanya diacak
    per sumber supaya satu sumber jelek tidak mendominasi antrean cek."""
    import random
    seen: set[str] = set()
    fresh, rest = [], []
    for batch in batches:
        for item in batch:
            key = f"{item['protocol']}://{item['proxy']}"
            if key in seen:
                continue
            seen.add(key)
            (fresh if is_fresh_source(item.get("source", "")) else rest).append(item)
    random.shuffle(rest)
    return fresh + rest


def harvest(protocols=None, country="", sources_path=None) -> list[dict]:
    """Satu pintu masuk: async bila aiohttp ada, fallback thread bila tidak.
    Proxy yang masuk blacklist (config/blacklist.txt) dibuang di sini."""
    from .blacklist import filter_blacklisted
    if HAS_AIOHTTP:
        out = asyncio.run(harvest_async(protocols, country, sources_path))
    else:
        out = harvest_threaded(protocols, country, sources_path)
    return filter_blacklisted(out)
