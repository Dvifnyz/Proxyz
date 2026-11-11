"""Proxyx — harvester: panen proxy publik dari semua sumber, satu pipeline.

Satu mesin panen (bukan tiga seperti repo asli). aiohttp bila tersedia,
fallback urllib ber-thread bila tidak. Verifikasi TLS TETAP NYALA —
repo asli mematikannya (verify=False / ssl=False); kami memakai
system CA store supaya tetap aman dan tetap jalan di mesin biasa.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import ssl
import urllib.request

from .sources import is_fresh_source, load_sources, parse_proxies_from_text, with_country

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Proxyx/1.0"}

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore
    HAS_AIOHTTP = False


def build_jobs(protocols: list[str] | None = None, country: str = "",
               sources_path: str | None = None) -> list[tuple[str, str]]:
    """Daftar (url, protokol). Urutan: sumber segar dulu di tiap protokol."""
    sources = load_sources(sources_path)
    if not protocols or "all" in protocols:
        wanted = [p for p in ("http", "socks4", "socks5") if p in sources]
    else:
        wanted = [p.lower() for p in protocols if p.lower() in sources]
    jobs: list[tuple[str, str]] = []
    for proto in wanted:
        urls = sorted(sources.get(proto, []), key=lambda u: (not is_fresh_source(u), u))
        for url in urls:
            jobs.append((with_country(url, country), proto))
    return jobs


# ------------------------------------------------------------------ aiohttp
async def _fetch_one(session, url: str, protocol: str) -> list[dict]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
            if r.status != 200:
                return []
            text = await r.text(errors="ignore")
    except Exception:
        return []
    return parse_proxies_from_text(text, protocol, source=url)


async def harvest_async(protocols=None, country="", sources_path=None) -> list[dict]:
    jobs = build_jobs(protocols, country, sources_path)
    # System CA store (verifikasi tetap nyala), bukan certifi saja.
    ctx = ssl.create_default_context()
    connector = aiohttp.TCPConnector(ssl=ctx, limit=35)
    # trust_env=True: hormati HTTP(S)_PROXY dari environment (penting di
    # mesin yang internetnya lewat proxy korporat/sandbox; di laptop biasa
    # variabel itu tidak ada, jadi tidak berpengaruh).
    async with aiohttp.ClientSession(headers=UA, connector=connector, trust_env=True) as session:
        batches = await asyncio.gather(*[_fetch_one(session, u, p) for u, p in jobs])
    return _dedup(batches)


# ------------------------------------------------------------------ fallback
def _fetch_one_urllib(job: tuple[str, str]) -> list[dict]:
    url, protocol = job
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=12) as r:
            if r.status != 200:
                return []
            text = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    return parse_proxies_from_text(text, protocol, source=url)


def harvest_threaded(protocols=None, country="", sources_path=None) -> list[dict]:
    jobs = build_jobs(protocols, country, sources_path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        batches = list(ex.map(_fetch_one_urllib, jobs))
    return _dedup(batches)


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
    """Satu pintu masuk: async bila aiohttp ada, fallback thread bila tidak."""
    if HAS_AIOHTTP:
        return asyncio.run(harvest_async(protocols, country, sources_path))
    return harvest_threaded(protocols, country, sources_path)
