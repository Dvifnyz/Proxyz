"""Proxyz — auto: panen + cek + ekspor berkala, tanpa henti.

`proxyz auto` menjalankan satu siklus penuh (panen -> cek hidup ->
ekspor + backup) tiap N menit, selamanya, sampai Ctrl+C. Cocok untuk
dijalankan sebagai service bersama gateway (atau via cron dengan
`--sekali` untuk satu siklus saja).

Fungsi panen/cek/ekspor bisa disuntikkan (dipakai tes) — default-nya
fungsi asli Proxyz.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime

from .checker import check_pool_sync
from .exporter import export_all
from .harvester import harvest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(BASE_DIR, "output", "scheduler.log")


def _log(msg: str, log_path: str | None = None) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(f"  {line}")
    if log_path:
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def run_cycle(harvest_fn=harvest, check_fn=check_pool_sync,
              export_fn=export_all, target: int = 20,
              out_dir: str | None = None,
              log_path: str | None = None) -> dict:
    """Satu siklus: panen -> cek -> ekspor. Kembalikan ringkasan."""
    out_dir = out_dir or os.path.join(BASE_DIR, "output")
    t0 = time.monotonic()
    kandidat = harvest_fn()
    hidup = check_fn(kandidat, target=target)
    paths = export_fn(hidup, out_dir) if hidup else {}
    dt = round(time.monotonic() - t0, 1)
    summary = {"raw": len(kandidat), "alive": len(hidup),
               "seconds": dt, "exported": list(paths)}
    _log(f"[auto] {len(kandidat):,} kandidat -> {len(hidup)} hidup "
         f"({dt} dtk)", log_path)
    return summary


def run_scheduler(interval_min: float = 60, target: int = 20,
                  stop_event: threading.Event | None = None,
                  once: bool = False, out_dir: str | None = None,
                  log_path: str | None = None, **cycle_kw) -> dict | None:
    """Loop selamanya (atau sekali bila once=True). Kembalikan ringkasan
    siklus terakhir."""
    stop = stop_event or threading.Event()
    last = None
    _log(f"[auto] mulai — siklus tiap {interval_min} menit, target {target} hidup",
         log_path)
    while True:
        last = run_cycle(target=target, out_dir=out_dir,
                         log_path=log_path, **cycle_kw)
        if once:
            return last
        if stop.wait(max(1.0, interval_min * 60)):
            _log("[auto] berhenti.", log_path)
            return last
