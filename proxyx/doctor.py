"""Proxyx — doctor: diagnosa mandiri sebelum bertanya.

Memeriksa Python, config, sumber, pool, key residential, dan apakah
gateway sedang jalan. Tidak mengubah apa pun, tidak mengirim data
ke mana pun. Dipakai pengguna saat ada yang tidak jalan, dan oleh
`proxyx update` sebelum update (bukan pengganti tes).
"""
from __future__ import annotations

import os
import shutil
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_doctor(base_dir: str | None = None, gateway_port: int | None = None,
               check_gateway: bool = True) -> dict:
    base = base_dir or BASE_DIR
    checks: list[dict] = []

    def add(name: str, ok: bool | None, detail: str = ""):
        checks.append({"name": name, "ok": ok, "detail": detail})

    add("Python", sys.version_info >= (3, 9),
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    try:
        from .config import load_config
        cfg = load_config(os.path.join(base, "config", "proxyx.json"))
        add("Config", 1024 <= cfg["gateway_port"] <= 65535,
            f"port {cfg['gateway_port']}, healer {cfg['healer_interval']} dtk")
    except Exception as e:
        cfg = {}
        add("Config", False, str(e)[:100])

    try:
        from .sources import load_sources
        src = load_sources(os.path.join(base, "config", "sources.json"))
        total = sum(len(v) for v in src.values())
        add("Sumber panen", total > 0, f"{total} URL ({', '.join(src)})")
    except Exception as e:
        add("Sumber panen", False, str(e)[:100])

    pool_path = os.path.join(base, "output", "proxy_hidup.txt")
    if os.path.exists(pool_path):
        with open(pool_path, encoding="utf-8", errors="ignore") as f:
            n = sum(1 for line in f if line.strip())
        add("Pool", n > 0, f"{n} proxy di output/proxy_hidup.txt")
    else:
        add("Pool", None, "belum ada — jalankan: python -m proxyx panen")

    try:
        from .residential import load_api_keys
        keys = load_api_keys()
        add("Residential Webshare", None if not keys else True,
            f"{len(keys)} API key tersimpan" if keys else "tidak ada key")
    except Exception as e:
        add("Residential Webshare", False, str(e)[:100])

    bl_path = os.path.join(base, "config", "blacklist.txt")
    if os.path.exists(bl_path):
        with open(bl_path, encoding="utf-8") as f:
            n_bl = sum(1 for line in f if line.strip() and not line.startswith("#"))
        add("Blacklist", True, f"{n_bl} entri")
    else:
        add("Blacklist", True, "tidak ada file (boleh kosong)")

    out_dir = os.path.join(base, "output")
    add("Output bisa ditulis", os.access(out_dir, os.W_OK) if os.path.exists(out_dir) else False,
        out_dir)
    try:
        free_gb = shutil.disk_usage(base).free / 1e9
        add("Ruang disk", free_gb > 0.1, f"{free_gb:.1f} GB bebas")
    except Exception as e:
        add("Ruang disk", False, str(e)[:100])

    if check_gateway:
        port = gateway_port or (cfg.get("gateway_port", 8888) if isinstance(cfg, dict) else 8888)
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/status", timeout=2) as r:
                import json
                data = json.loads(r.read())
            add("Gateway", True, f"jalan di :{port} ({data.get('pool', 0)} proxy)")
        except Exception:
            add("Gateway", None, f"tidak jalan di :{port} (normal bila belum dinyalakan)")

    errors = sum(1 for c in checks if c["ok"] is False)
    warnings = sum(1 for c in checks if c["ok"] is None)
    return {"checks": checks, "errors": errors, "warnings": warnings,
            "healthy": errors == 0}


def print_doctor(result: dict) -> None:
    print("\n  🩺 Proxyx Doctor")
    for c in result["checks"]:
        mark = "✅" if c["ok"] is True else ("⚠️" if c["ok"] is None else "❌")
        print(f"  {mark} {c['name']}: {c['detail']}")
    if result["healthy"]:
        print(f"\n  ✅ Sehat ({result['warnings']} peringatan, 0 error).")
    else:
        print(f"\n  ❌ {result['errors']} error, {result['warnings']} peringatan — "
              "perbaiki yang bertanda ❌ dulu.")
