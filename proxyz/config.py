"""Proxyz — konfigurasi: SATU sumber yang benar-benar dibaca kode.

Repo asli punya variabel .env (GATEWAY_PORT, AUTO_HEALER_INTERVAL, ...)
yang TIDAK DIBACA oleh kode Python mana pun — konfigurasi mati.
Di Proxyz, semua setting dibaca dari sini:
  1. default bawaan,
  2. ditimpa config/proxyz.json (bila ada),
  3. ditimpa environment (GATEWAY_PORT, PROXYZ_TOKEN, ...).

API key / token TIDAK PERNAH ditulis ke file config ini — token lewat
env PROXYZ_TOKEN, API key Webshare lewat env/config webshare.json.
"""
from __future__ import annotations

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config", "proxyz.json")

DEFAULTS = {
    "gateway_port": 8888,
    "gateway_host": "127.0.0.1",   # sengaja localhost saja — jangan expose ke LAN
    "healer_interval": 90,         # detik antar siklus healer
    "min_healthy": 5,              # refill bila pool < ini
    "healer_target": 10,           # target isi ulang
    "check_timeout": 5.0,          # detik per proxy saat cek
    "check_workers": 100,
    "check_target": 20,            # target proxy hidup default saat panen
    "max_latency_ms": 1200,        # di atas ini dianggap terlalu lambat
    "session_ttl": 600,            # sticky session (detik)
    "rate_limit_per_min": 60,      # batas request /api/* per IP per menit (0 = bebas)
    "audit_log": True,             # tulis output/gateway-audit.jsonl
    "schedule_interval_min": 60,   # jeda antar siklus `proxyz auto`
    "schedule_target": 20,         # target proxy hidup per siklus auto
}

ENV_MAP = {
    "GATEWAY_PORT": ("gateway_port", int),
    # PROXYX_TOKEN = nama lama (v2.x), tetap dibaca; PROXYZ_TOKEN menang bila keduanya ada.
    "PROXYX_TOKEN": ("token", str),
    "PROXYZ_TOKEN": ("token", str),
    "HEALER_INTERVAL": ("healer_interval", int),
    "MIN_HEALTHY": ("min_healthy", int),
    "CHECK_TIMEOUT": ("check_timeout", float),
}

# Profil gateway (baru di Proxyz — repo asli punya 3 profil di menu,
# tapi hanya label; di sini tiap profil benar-benar mengubah perilaku):
# - scraper: rotasi agresif, pool besar (tiap request ganti IP)
# - cepat:  hanya proxy <=350 ms yang dipakai
# - hemat:   pool kecil, sesi lama, refill jarang (irit kuota & CPU)
PROFILES = {
    "scraper": {"healer_target": 30, "min_healthy": 10, "session_ttl": 60,
                "max_latency_ms": 1200},
    "cepat": {"healer_target": 10, "min_healthy": 5, "session_ttl": 600,
              "max_latency_ms": 350},
    "hemat": {"healer_target": 5, "min_healthy": 2, "session_ttl": 1800,
              "max_latency_ms": 1200},
}


def apply_profile(cfg: dict, name: str) -> dict:
    """Terapkan preset profil ke salinan config. Nama tidak dikenal = tidak berubah."""
    out = dict(cfg)
    if name in PROFILES:
        out.update(PROFILES[name])
    return out


def load_config(path: str | None = None) -> dict:
    """Baca config: default -> file -> env. Selalu kembalikan dict lengkap."""
    cfg = dict(DEFAULTS)
    cfg["token"] = ""
    path = path or CONFIG_FILE
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in DEFAULTS:
                    cfg[k] = v
        except Exception:
            pass
    for env_key, (name, cast) in ENV_MAP.items():
        raw = os.environ.get(env_key)
        if raw not in (None, ""):
            try:
                cfg[name] = cast(raw)
            except (ValueError, TypeError):
                pass
    return cfg
