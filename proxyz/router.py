"""Proxyz — sinkronisasi pool ke 9Router (SQLite `proxyPools`).

Fitur ini ADA di petani-proxy (exporter.py / fast_validator.py /
warp_generator.py) dan di-port ke sini dengan satu perbedaan penting:

Repo asli: `replace=True` menghapus baris `WHERE data LIKE
'%PetaniProxy%' OR data LIKE '%OmniProxy%' OR testStatus='unknown'`
— termasuk baris 'unknown' yang BUKAN miliknya. Itu destruktif.

Proxyz: insert-only secara default. Baris lama TIDAK PERNAH dihapus
kecuali dengan `--ganti`, dan itupun HANYA baris yang ditandai
'Proxyz' milik tool ini sendiri — baris 9Router lain dan baris
'unknown' tidak disentuh. Sebelum menulis apa pun, file DB di-backup
dulu (`data.sqlite.bak-<waktu>`).

9Router adalah aplikasi router milik pengguna sendiri; sinkronisasi
ini hanya menulis ke DB SQLite lokal yang ditunjuk pengguna.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
import uuid
from datetime import datetime, timezone

from .models import Proxy


def find_9router_db() -> str | None:
    """Cari DB 9Router: env dulu, lalu folder saudara (pola repo asli)."""
    for env_key in ("ROUTER_DB_PATH", "BANSOS_ROUTER_DB", "NINEROUTER_DB"):
        path = os.environ.get(env_key)
        if path and os.path.exists(path):
            return path
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("9router-mibp-version", "9router", "eLrouter", "bansos-router"):
        cand = os.path.normpath(os.path.join(base, "..", name, "data", "db", "data.sqlite"))
        if os.path.exists(cand):
            return cand
    return None


def _table_ok(conn: sqlite3.Connection) -> bool:
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='proxyPools'")
        return cur.fetchone() is not None
    except Exception:
        return False


def backup_db(db_path: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{db_path}.bak-{stamp}"
    n = 1
    while os.path.exists(bak):
        n += 1
        bak = f"{db_path}.bak-{stamp}-{n}"
    shutil.copy2(db_path, bak)
    return bak


def sync_to_9router(proxies: list[Proxy], db_path: str,
                    replace: bool = False) -> dict:
    """Tulis proxy hidup ke proxyPools. Kembalikan ringkasan.
    - backup dulu, lalu insert; proxy yang sudah ada (proxyUrl sama)
      dilewati (dedup) supaya sync berulang tidak menumpuk duplikat.
    - replace=True: hapus HANYA baris bertanda 'Proxyz' sebelum insert.
    """
    if not os.path.exists(db_path):
        return {"ok": False, "error": f"DB tidak ditemukan: {db_path}"}
    bak = backup_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        if not _table_ok(conn):
            return {"ok": False, "error": "tabel proxyPools tidak ada di DB ini",
                    "backup": bak}
        now_iso = datetime.now(timezone.utc).isoformat()
        deleted = 0
        if replace:
            # Hapus baris milik tool ini — nama baru "Proxyz" maupun
            # nama lama "Proxyx" (v2.x) — dan hanya itu.
            cur = conn.execute(
                "DELETE FROM proxyPools WHERE data LIKE '%\"name\": \"Proxyz%'"
                " OR data LIKE '%\"name\": \"Proxyx%'")
            deleted = cur.rowcount
        existing = {row[0] for row in conn.execute(
            "SELECT json_extract(data, '$.proxyUrl') FROM proxyPools")}
        inserted = skipped = 0
        for p in proxies:
            url = p.url
            if url in existing:
                skipped += 1
                continue
            payload = {
                "name": f"Proxyz [{p.country_code or '??'}] {p.hostport} ({p.protocol})",
                "proxyUrl": url,
                "noProxy": "",
                "type": p.protocol,
                "strictProxy": False,
                "lastTestedAt": now_iso,
                "lastError": None,
                "latency": round((p.ms or 1000) / 1000.0, 2),
                "egressIp": p.ip,
                "country": p.country_code or "??",
            }
            conn.execute(
                "INSERT INTO proxyPools (id, isActive, testStatus, data, createdAt, updatedAt)"
                " VALUES (?, 1, 'working', ?, ?, ?)",
                (str(uuid.uuid4()), json.dumps(payload), now_iso, now_iso))
            inserted += 1
        conn.commit()
        return {"ok": True, "inserted": inserted, "skipped": skipped,
                "deleted": deleted, "backup": bak, "db": db_path}
    finally:
        conn.close()
