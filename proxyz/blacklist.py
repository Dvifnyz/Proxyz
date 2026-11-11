"""Proxyz — blacklist: proxy yang tidak boleh dipakai lagi.

Satu file teks `config/blacklist.txt`, satu entri per baris:
  1.2.3.4          (blokir semua port IP itu)
  1.2.3.4:8080     (blokir satu proxy saja)
Baris `#` = komentar. Dipakai saat panen & cek — proxy yang masuk
daftar ini tidak pernah lolos ke pool.
"""
from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLACKLIST_FILE = os.path.join(BASE_DIR, "config", "blacklist.txt")


def load_blacklist(path: str | None = None) -> set[str]:
    path = path or BLACKLIST_FILE
    out: set[str] = set()
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.add(line)
    return out


def _save(entries: set[str], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(e + "\n" for e in sorted(entries))
    os.replace(tmp, path)


def add_to_blacklist(entry: str, path: str | None = None) -> bool:
    """True bila entri baru ditambahkan, False bila sudah ada."""
    path = path or BLACKLIST_FILE
    entries = load_blacklist(path)
    entry = entry.strip()
    if not entry or entry in entries:
        return False
    entries.add(entry)
    _save(entries, path)
    return True


def remove_from_blacklist(entry: str, path: str | None = None) -> bool:
    path = path or BLACKLIST_FILE
    entries = load_blacklist(path)
    if entry.strip() not in entries:
        return False
    entries.discard(entry.strip())
    _save(entries, path)
    return True


def is_blacklisted(proxy, entries: set[str] | None = None) -> bool:
    entries = entries if entries is not None else load_blacklist()
    if not entries:
        return False
    hostport = getattr(proxy, "hostport", None) or f"{proxy['ip']}:{proxy['port']}"
    ip = getattr(proxy, "ip", None) or proxy["ip"]
    return hostport in entries or ip in entries


def filter_blacklisted(proxies: list, entries: set[str] | None = None) -> list:
    entries = entries if entries is not None else load_blacklist()
    if not entries:
        return list(proxies)
    return [p for p in proxies if not is_blacklisted(p, entries)]
