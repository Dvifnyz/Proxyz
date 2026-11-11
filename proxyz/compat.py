"""Kompatibilitas: aiohttp opsional.

Dulu blok try/except ini diduplikat di checker.py dan harvester.py
(pylint R0801) — sekarang satu tempat. Tanpa aiohttp, kedua modul
jatuh ke fallback urllib ber-thread. `HAS_AIOHTTP` dipakai pengetes
untuk tahu jalur mana yang aktif.
"""
from __future__ import annotations

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:  # pragma: no cover - aiohttp selalu ada di dev
    aiohttp = None  # type: ignore[assignment]
    HAS_AIOHTTP = False

__all__ = ["HAS_AIOHTTP", "aiohttp"]
