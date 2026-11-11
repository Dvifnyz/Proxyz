"""Proxyz — laporan: ringkasan kesehatan pool dalam satu halaman.

Sumber data: pool di disk, skor kesehatan sumber, hasil bench terakhir.
Tidak mengambil data baru dari internet — laporan hanya merangkum
apa yang sudah diketahui Proxyz.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime

from .models import Proxy
from .tiers import tier_of

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_report(pool: list[Proxy], health_rows: list[dict] | None = None,
                 bench_results: list[dict] | None = None,
                 stats: dict | None = None) -> dict:
    health_rows = health_rows or []
    bench_results = bench_results or []
    by_protocol = Counter(p.protocol for p in pool)
    by_country = Counter(p.country_code or "??" for p in pool)
    by_tier = Counter(tier_of(p) for p in pool)
    top_sources = sorted(health_rows, key=lambda r: -r.get("yield", 0))[:5]
    dead_sources = [r for r in health_rows if r.get("fails", 0) >= 3]
    bench_ok = [b for b in bench_results if b.get("ok")]
    bench_ok.sort(key=lambda b: -b.get("kbps", 0))
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pool_total": len(pool),
        "by_protocol": dict(by_protocol),
        "by_country": dict(by_country.most_common(5)),
        "by_tier": dict(by_tier),
        "top_sources": [{"url": r["url"][:60], "yield": r.get("yield", 0)}
                        for r in top_sources],
        "dead_sources": len(dead_sources),
        "bench_top": [{"proxy": b["proxy"], "kbps": b.get("kbps")}
                      for b in bench_ok[:3]],
        "stats": stats or {},
    }


def report_markdown(data: dict) -> str:
    lines = [f"# Laporan Proxyz — {data['generated_at']}", "",
             f"**Pool:** {data['pool_total']} proxy",
             f"**Protokol:** {data['by_protocol']}",
             f"**Negara teratas:** {data['by_country']}",
             f"**Tier:** {data['by_tier']}",
             f"**Sumber mati (backoff):** {data['dead_sources']}", ""]
    lines.append("## Sumber paling produktif")
    for s in data["top_sources"]:
        lines.append(f"- {s['url']} — {s['yield']:,} hasil")
    if not data["top_sources"]:
        lines.append("- (belum ada riwayat panen)")
    lines.append("")
    lines.append("## Proxy tercepat (bench terakhir)")
    for b in data["bench_top"]:
        lines.append(f"- {b['proxy']} — {b['kbps']} KB/detik")
    if not data["bench_top"]:
        lines.append("- (belum ada hasil bench — jalankan `proxyz bench`)")
    if data.get("stats"):
        s = data["stats"]
        lines += ["", "## Gateway",
                  (f"- Request: {s.get('total_requests', 0)} "
                   f"({s.get('success_pct', 0)}% sukses)"),
                  f"- Evicted: {s.get('evicted', 0)}",
                  f"- Uptime: {s.get('uptime_sec', 0)} dtk"]
    return "\n".join(lines) + "\n"


def load_bench_results(path: str | None = None) -> list[dict]:
    path = path or os.path.join(BASE_DIR, "output", "bench.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
