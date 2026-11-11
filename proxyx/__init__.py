"""Shim kompatibilitas: paket `proxyx` berganti nama menjadi `proxyz` di v2.1.0.

Paket ini hanya meneruskan ke `proxyz`. Untuk kode baru, pakai
`import proxyz` dan `python -m proxyz`. Shim ini dipertahankan sampai
v3.0.0, lalu dihapus (lihat docs/MIGRASI-2.1.md).
"""
from __future__ import annotations

import importlib
import sys
import warnings

warnings.warn(
    "Paket 'proxyx' sudah berganti nama menjadi 'proxyz' (v2.1.0). "
    "Ganti `import proxyx` dengan `import proxyz`.",
    DeprecationWarning, stacklevel=2)

from proxyz import __version__

__all__ = ["__version__"]

# Daftarkan semua submodul proxyz sebagai proxyx.* supaya
# `from proxyx.gateway import ...` tetap jalan.
_SUBMODULES = (
    "bench", "blacklist", "checker", "cli", "compat", "config",
    "doctor", "exporter", "gateway", "harvester", "installer",
    "models", "pool", "report", "residential", "router",
    "scheduler", "sources", "tiers", "updater", "warp",
)
for _name in _SUBMODULES:
    sys.modules[__name__ + "." + _name] = importlib.import_module(f"proxyz.{_name}")


def __getattr__(name: str):
    return importlib.import_module(f"proxyz.{name}")


def __dir__() -> list[str]:
    return sorted(__all__ + ["__version__"])
