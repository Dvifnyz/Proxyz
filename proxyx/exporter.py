"""Proxyx — ekspor hasil panen: TXT, JSON, CSV, Clash YAML.

Penulisan atomik (temp + os.replace) — repo asli menulis langsung dan
file bisa terbaca setengah bila proses mati di tengah jalan.
"""
from __future__ import annotations

import json
import os

from .models import Proxy


def _atomic(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)
    return path


def export_txt(proxies: list[Proxy], path: str) -> str:
    return _atomic(path, "\n".join(p.url for p in proxies) + ("\n" if proxies else ""))


def export_json(proxies: list[Proxy], path: str) -> str:
    return _atomic(path, json.dumps([p.to_dict() for p in proxies], indent=2))


def export_csv(proxies: list[Proxy], path: str) -> str:
    lines = ["protocol,ip,port,ms,anonymity,score,country_code,country,city,isp,residential"]
    for p in proxies:
        lines.append(f"{p.protocol},{p.ip},{p.port},{p.ms or ''},{p.anonymity},"
                     f"{p.score},{p.country_code},{p.country},{p.city},{p.isp},"
                     f"{int(p.residential)}")
    return _atomic(path, "\n".join(lines) + "\n")


def export_clash(proxies: list[Proxy], path: str) -> str:
    """Clash YAML: tiap proxy jadi entri + satu grup `PROXYX` (url-test).
    Hanya HTTP & SOCKS5 yang didukung Clash (SOCKS4 dilewati)."""
    lines = ["proxies:"]
    names = []
    for i, p in enumerate(proxies):
        if p.protocol not in ("http", "socks5"):
            continue
        name = f"proxyx-{i + 1}-{p.ip.replace('.', '-')}"
        names.append(name)
        lines.append(f"  - name: {name}")
        lines.append(f"    type: {'http' if p.protocol == 'http' else 'socks5'}")
        lines.append(f"    server: {p.ip}")
        lines.append(f"    port: {p.port}")
        if p.username:
            lines.append(f"    username: {p.username}")
            lines.append(f"    password: {p.password}")
    lines.append("proxy-groups:")
    lines.append("  - name: PROXYX")
    lines.append("    type: url-test")
    lines.append("    url: http://www.gstatic.com/generate_204")
    lines.append("    interval: 300")
    lines.append("    proxies:")
    for n in names:
        lines.append(f"      - {n}")
    return _atomic(path, "\n".join(lines) + "\n")


def export_all(proxies: list[Proxy], out_dir: str) -> dict[str, str]:
    """Ekspor ke semua format. Kembalikan {format: path}."""
    return {
        "txt": export_txt(proxies, os.path.join(out_dir, "proxy_hidup.txt")),
        "json": export_json(proxies, os.path.join(out_dir, "proxy_hidup.json")),
        "csv": export_csv(proxies, os.path.join(out_dir, "proxy_hidup.csv")),
        "clash": export_clash(proxies, os.path.join(out_dir, "proxy_clash.yaml")),
    }
