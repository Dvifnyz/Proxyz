"""Proxyz — tier kecepatan: cepat / sedang / lambat.

  cepat : latency <= 350 ms   (buat browsing & scraping responsif)
  sedang: latency <= 800 ms
  lambat: sisanya (termasuk yang latensinya tidak diketahui)
"""
from __future__ import annotations

TIERS = {"cepat": 350, "sedang": 800, "lambat": None}


def tier_of(proxy) -> str:
    ms = getattr(proxy, "ms", None)
    if ms is None:
        ms = proxy.get("ms") if isinstance(proxy, dict) else None
    if ms is None:
        return "lambat"
    if ms <= 350:
        return "cepat"
    if ms <= 800:
        return "sedang"
    return "lambat"


def filter_tier(proxies: list, tier: str) -> list:
    if tier not in TIERS:
        return list(proxies)
    if tier == "lambat":
        return list(proxies)
    limit = TIERS[tier]
    out = []
    for p in proxies:
        ms = getattr(p, "ms", None)
        if ms is None:
            ms = p.get("ms") if isinstance(p, dict) else None
        if ms is not None and ms <= limit:
            out.append(p)
    return out
