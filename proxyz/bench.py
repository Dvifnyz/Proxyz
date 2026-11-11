"""Proxyz — bench: ukur kecepatan unduh tiap proxy (KB/detik).

Mengunduh file uji dari Cloudflare (speed.cloudflare.com/__down)
lewat tiap proxy, lalu diranking dari yang tercepat. Bukan sekadar
latensi ping — ini kecepatan nyata saat dipakai browsing/download.

Hanya proxy HTTP yang bisa di-bench di sini (urllib tidak bisa SOCKS);
SOCKS dilewati dengan alasan yang jelas, bukan diam-diam.
"""
from __future__ import annotations

import concurrent.futures
import time
import urllib.request

from .models import Proxy

SPEED_URL = "https://speed.cloudflare.com/__down?bytes={n}"


def _bench_one(proxy: Proxy, n_bytes: int, timeout: float) -> dict:
    if proxy.protocol != "http":
        return {"proxy": proxy.hostport, "ok": False,
                "error": "SOCKS tidak didukung bench (hanya HTTP)"}
    handler = urllib.request.ProxyHandler({"http": proxy.url, "https": proxy.url})
    opener = urllib.request.build_opener(handler)
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(SPEED_URL.format(n=n_bytes),
                                     headers={"User-Agent": "Proxyz/1.0"})
        with opener.open(req, timeout=timeout) as r:
            got = 0
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                got += len(chunk)
        dt = time.monotonic() - t0
        return {"proxy": proxy.hostport, "ok": True, "bytes": got,
                "seconds": round(dt, 2),
                "kbps": round(got / dt / 1024, 1) if dt > 0 else 0.0}
    except Exception as e:
        return {"proxy": proxy.hostport, "ok": False, "error": str(e)[:120]}


def bench_pool(proxies: list[Proxy], n_bytes: int = 1_000_000,
               timeout: float = 15.0, workers: int = 10) -> list[dict]:
    """Ranking kecepatan: yang berhasil dulu (tercepat di atas),
    lalu yang gagal beserta alasannya."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda p: _bench_one(p, n_bytes, timeout), proxies))
    ok = sorted([r for r in results if r["ok"]], key=lambda r: -r["kbps"])
    bad = [r for r in results if not r["ok"]]
    return ok + bad
