"""Proxyz — WARP: akun Cloudflare WARP resmi -> WireGuard + Sing-box.

Diambil dari pola repo asli (warp_generator.py) yang sudah benar:
registrasi via API resmi Cloudflare (sah, tanpa captcha). Diperbaiki:
- Keygen fallback `wg genkey` bila `cryptography` tidak ada (asli langsung error).
- File disimpan mode 0600 + peringatan jangan dibagikan (asli menyimpan
  token polos tanpa peringatan, bahkan contohnya ikut ter-commit).
- Tanpa sync 9Router (dan tanpa bug variabel db_path-nya).
- Multi-profil: --jumlah N menghasilkan N akun.
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import subprocess
import urllib.request
import uuid

REG_API = "https://api.cloudflareclient.com/v0a2158/reg"
UA = {"User-Agent": "okhttp/3.12.1"}


def generate_keypair() -> tuple[str, str]:
    """(private_b64, public_b64) X25519. Coba cryptography, lalu `wg`."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import x25519
        priv = x25519.X25519PrivateKey.generate()
        priv_b = base64.b64encode(priv.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
            serialization.NoEncryption())).decode()
        pub_b = base64.b64encode(priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        return priv_b, pub_b
    except ImportError:
        pass
    try:
        priv = subprocess.check_output(["wg", "genkey"], text=True).strip()
        pub = subprocess.check_output(["wg", "pubkey"], input=priv, text=True).strip()
        return priv, pub
    except Exception as e:
        raise RuntimeError(
            "Butuh `cryptography` (pip install cryptography) atau aplikasi "
            "WireGuard (`wg`).") from e


def register_account() -> dict:
    """Daftar 1 akun WARP via API resmi. Kembalikan dict profil."""
    priv_b, pub_b = generate_keypair()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
    payload = {"key": pub_b, "install_id": uuid.uuid4().hex, "fcm_token": "",
               "tos": now, "model": "PC", "serial_number": "", "locale": "en_US"}
    req = urllib.request.Request(
        REG_API, data=json.dumps(payload).encode(),
        headers={**UA, "Content-Type": "application/json; charset=UTF-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status not in (200, 201):
                raise RuntimeError(f"WARP API status {r.status}")
            data = json.loads(r.read().decode())
    except Exception as e:
        raise RuntimeError(f"Gagal daftar ke API Cloudflare: {e}") from e
    cfg = data.get("config", {})
    peers = cfg.get("peers", [])
    peer = peers[0] if peers else {}
    endpoint = peer.get("endpoint", {}).get("host", "")
    peer_pub = peer.get("public_key", "")
    if not endpoint or not peer_pub:
        raise RuntimeError("Respons WARP tidak lengkap (tanpa peer/endpoint)")
    addr = cfg.get("interface", {}).get("addresses", {})
    v4 = addr.get("v4", "172.16.0.2/32")
    v6 = addr.get("v6", "")
    return {"account_id": data.get("id"), "token": data.get("token"),
            "private_key": priv_b, "public_key": pub_b,
            "peer_public_key": peer_pub, "endpoint": endpoint,
            "v4": v4, "v6": v6, "dns": "1.1.1.1, 1.0.0.1"}


def build_wireguard_conf(p: dict) -> str:
    addr = p["v4"] + (f", {p['v6']}" if p["v6"] else "")
    return ("[Interface]\n"
            f"PrivateKey = {p['private_key']}\n"
            f"Address = {addr}\n"
            f"DNS = {p['dns']}\n\n"
            "[Peer]\n"
            f"PublicKey = {p['peer_public_key']}\n"
            "AllowedIPs = 0.0.0.0/0, ::/0\n"
            f"Endpoint = {p['endpoint']}\n")


def build_singbox_config(p: dict) -> dict:
    return {
        "log": {"level": "info"},
        "inbounds": [{"type": "mixed", "tag": "mixed-in",
                      "listen": "127.0.0.1", "listen_port": 10808}],
        "outbounds": [{
            "type": "wireguard", "tag": "warp-out",
            "server": p["endpoint"].rsplit(":", 1)[0],
            "server_port": int(p["endpoint"].rsplit(":", 1)[1]),
            "local_address": [a.strip() for a in
                              (p["v4"] + (f",{p['v6']}" if p["v6"] else "")).split(",")],
            "private_key": p["private_key"],
            "peer_public_key": p["peer_public_key"],
            "reserved": [0, 0, 0],
        }],
    }


def _write_private(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)  # atomik — asli menulis langsung (bisa terbaca setengah)
    return path


def generate_and_save(out_dir: str, count: int = 1) -> list[dict]:
    """Buat `count` profil WARP. Kembalikan daftar profil (tanpa token
    di log — token hanya ada di file warp-N.json mode 0600)."""
    os.makedirs(out_dir, exist_ok=True)
    profiles = []
    for i in range(count):
        p = register_account()
        suffix = "" if count == 1 else f"-{i + 1}"
        _write_private(os.path.join(out_dir, f"warp{suffix}.conf"),
                       build_wireguard_conf(p))
        _write_private(os.path.join(out_dir, f"warp{suffix}_singbox.json"),
                       json.dumps(build_singbox_config(p), indent=2))
        _write_private(os.path.join(out_dir, f"warp{suffix}.json"),
                       json.dumps(p, indent=2))
        profiles.append(p)
    return profiles
