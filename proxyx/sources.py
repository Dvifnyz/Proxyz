"""Proxyx — daftar sumber proxy publik (satu sumber kebenaran).

Semua sumber dibaca dari SATU file: config/sources.json.
Tidak ada daftar hardcode kedua (cacat repo asli: FAST_SOURCES terpisah
yang bisa divergen dari sources.json).
"""
from __future__ import annotations

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCES = os.path.join(BASE_DIR, "config", "sources.json")

PROXY_RE = re.compile(
    r"(?<![\d.])"  # jangan cocok dengan ekor "56.0.0.1" dari "256.0.0.1"
    r"(?:(?P<proto>https?|socks4|socks5)://)?"
    r"(?P<ip>(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})"
    r":(?P<port>\d{2,5})(?!\d)",
    re.IGNORECASE,
)


def load_sources(path: str | None = None) -> dict[str, list[str]]:
    """Baca sources.json -> {protocol: [url, ...]}. File hilang = dict kosong."""
    path = path or DEFAULT_SOURCES
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k.lower(): list(v) for k, v in data.items() if isinstance(v, list)}


def parse_proxies_from_text(text: str, protocol: str, source: str = "") -> list[dict]:
    """Parse semua `IP:port` dari isi satu feed. Kembalikan dict mentah
    (checker yang mengubahnya jadi Proxy)."""
    out = []
    for m in PROXY_RE.finditer(text or ""):
        port = int(m.group("port"))
        if 1 <= port <= 65535:
            out.append({"ip": m.group("ip"), "port": port,
                        "proxy": f"{m.group('ip')}:{port}",
                        "protocol": protocol, "source": source or protocol})
    return out


def is_fresh_source(url: str) -> bool:
    """Sumber live (API yang di-generate tiap request) didahulukan saat cek."""
    return "proxyscrape.com" in url or "proxy-list.download" in url


def with_country(url: str, country: str) -> str:
    """Filter negara hanya didukung proxyscrape — sumber lain diabaikan
    (jujur: jangan klaim filter 150+ negara kalau sumbernya tidak mendukung)."""
    if country and "proxyscrape.com" in url and "country=all" in url:
        return url.replace("country=all", f"country={country.upper()}")
    return url
