"""Proxyz — proxy residential: jalur resmi, bukan farm akun.

Kenapa begini (baca sebelum protes):
-----------------------------------
Repo asli mendapatkan IP residential dengan cara membuat BANYAK akun
gratis Webshare secara otomatis: email sekali pakai + pemecah captcha
suara + browser automation. Di lapangan cara itu rapuh dan pendek umur:
  - Webshare mendeteksi pola itu (domain sekali pakai, sidik solver audio,
    perilaku browser otomatis) dan akunnya cepat di-banned — proxy ikut mati.
  - Tiap Webshare mengubah DOM / reCAPTCHA, hunter-nya rusak total.
  - Akun yang dibuat otomatis juga melanggar ToS Webshare.

Proxyz mengambil jalur yang justru bikin residential-nya AWET:
  1. Kamu daftar SATU akun Webshare sendiri (manusia, captcha diisi
     sendiri sekali, 30 detik) di https://proxy.webshare.io/register
  2. Ambil API key dari dashboard (gratis, 10 proxy untuk akun free)
  3. Proxyz menarik daftar proxymu lewat API RESMI Webshare dan
     memasukkannya ke pool yang sama dengan proxy publik — gateway
     memutar semuanya, residential diprioritaskan (skor +20).
  4. Punya proxy berbayar/residential dari penyedia lain? Tempel
     `proto://user:pass@ip:port` ke output/proxy_manual.txt — ikut ke pool.

Tidak ada pemecah captcha otomatis, tidak ada farm akun massal, tidak
ada bypass Turnstile di tool ini. Bukan karena tidak bisa — karena yang
otomatis itu hasilnya akun keblokir dan proxy mati, sementara jalur API
ini yang justru membuat 10 IP gratis itu tetap hidup.
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import secrets
import string
import urllib.error
import urllib.request
import webbrowser

from .models import Proxy

log = logging.getLogger(__name__)

WEBSHARE_API = "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page_size=100"
WEBSHARE_REGISTER = "https://proxy.webshare.io/register"
UA = {"User-Agent": "Proxyz/1.0"}
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL_FILE = os.path.join(BASE_DIR, "output", "proxy_manual.txt")
KEY_FILE = os.path.join(BASE_DIR, "config", "webshare.json")


def load_api_keys() -> list[str]:
    """Semua API key: env WEBSHARE_API_KEY (satu, dipisah koma bila banyak)
    + config/webshare.json lokal ({"api_keys": [...]}).
    v2.0.0: format lama {"api_key": "..."} dimigrasi OTOMATIS ke format
    list saat pertama dibaca (file ditulis ulang, isi key sama).
    File itu di-gitignore — jangan pernah commit key."""
    keys: list[str] = []
    env = os.environ.get("WEBSHARE_API_KEY", "")
    keys += [k.strip() for k in env.split(",") if k.strip()]
    migrated = False
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("api_keys"), list):
                keys += [str(k).strip() for k in data["api_keys"] if str(k).strip()]
            elif data.get("api_key"):
                keys.append(str(data["api_key"]).strip())
                migrated = True
        except Exception:
            pass
    out, seen = [], set()
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    if migrated:
        # Tulis ulang ke format v2.0.0 (diam-diam; tidak mengubah key).
        try:
            with open(KEY_FILE, "w", encoding="utf-8") as f:
                json.dump({"api_keys": out}, f)
            os.chmod(KEY_FILE, 0o600)
        except Exception:
            pass
    return out


def load_api_key() -> str:
    """Satu key pertama (kompatibilitas lama)."""
    keys = load_api_keys()
    return keys[0] if keys else ""


def save_api_key(key: str) -> str:
    """Tambah key ke daftar lokal (config/webshare.json, 0600, bukan repo).
    Key yang sama tidak disimpan dua kali."""
    keys = load_api_keys()
    if key not in keys:
        keys.append(key)
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        json.dump({"api_keys": keys}, f)
    with contextlib.suppress(Exception):
        os.chmod(KEY_FILE, 0o600)
    return KEY_FILE


def validate_api_key(key: str) -> tuple[bool, str]:
    """Validasi key SECARA LIVE ke API Webshare. Kembalikan
    (True, 'N proxy') atau (False, 'alasan')."""
    try:
        proxies = fetch_webshare(key)
        return True, f"{len(proxies)} proxy"
    except ValueError:
        return False, "API key ditolak Webshare (401/403)"
    except RuntimeError as e:
        return False, str(e)


def fetch_all_webshare(keys: list[str] | None = None) -> list[Proxy]:
    """Tarik proxy dari SEMUA akun Webshare (multi-akun) + dedup.
    Akun yang key-nya mati dilewati diam-diam (akun lain tetap jalan)."""
    keys = keys if keys is not None else load_api_keys()
    out: list[Proxy] = []
    seen: set[str] = set()
    for key in keys:
        try:
            for p in fetch_webshare(key):
                if p.hostport not in seen:
                    seen.add(p.hostport)
                    out.append(p)
        except Exception as e:
            log.debug("fetch_webshare gagal untuk satu key: %s", e)
            continue
    return out


def fetch_webshare(api_key: str, timeout: float = 15.0) -> list[Proxy]:
    """Tarik daftar proxy residential via API resmi Webshare.
    Raises ValueError('auth') bila key salah, RuntimeError bila API gagal."""
    req = urllib.request.Request(
        WEBSHARE_API, headers={**UA, "Authorization": f"Token {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ValueError("auth") from e
        raise RuntimeError(f"Webshare API HTTP {e.code}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e
    out: list[Proxy] = []
    for row in data.get("results", []):
        ip = row.get("proxy_address", "")
        port = int(row.get("port") or row.get("ports", {}).get("http") or 0)
        if not ip or not port:
            continue
        out.append(Proxy(
            protocol="http", ip=ip, port=port,
            username=row.get("username", ""), password=row.get("password", ""),
            country_code=row.get("country_code", "") or "",
            source="webshare", residential=True))
    return out


def load_manual(path: str | None = None) -> list[Proxy]:
    """Baca output/proxy_manual.txt — satu proxy per baris, format
    `proto://user:pass@ip:port` atau `ip:port`. Baris `#` = komentar."""
    path = path or MANUAL_FILE
    out: list[Proxy] = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            p = Proxy.from_string(line, source="manual")
            if p:
                if p.username:  # proxy ber-auth = hampir pasti privat/residential
                    p.residential = True
                out.append(p)
    return out


def guided_signup(open_browser: bool = True) -> str:
    """Bantu daftar manual: buatkan password kuat + buka halaman daftar.
    Captcha diisi sendiri oleh pengguna (sekali, 30 detik)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    # Dijamin ada huruf kecil + besar + angka + simbol (bukan acak murni).
    parts = [secrets.choice(string.ascii_lowercase),
             secrets.choice(string.ascii_uppercase),
             secrets.choice(string.digits),
             secrets.choice("!@#$%^&*")]
    parts += [secrets.choice(alphabet) for _ in range(12)]
    secrets.SystemRandom().shuffle(parts)
    password = "".join(parts)
    if open_browser:
        with contextlib.suppress(Exception):
            webbrowser.open(WEBSHARE_REGISTER)
    return password
