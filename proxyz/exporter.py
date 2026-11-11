"""Proxyz — ekspor hasil panen: TXT, JSON, CSV, Clash YAML.

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


def clash_yaml(proxies: list[Proxy]) -> str:
    """Clash YAML sebagai string (dipakai file ekspor + endpoint live)."""
    lines = ["proxies:"]
    names = []
    for i, p in enumerate(proxies):
        if p.protocol not in ("http", "socks5"):
            continue
        name = f"proxyz-{i + 1}-{p.ip.replace('.', '-')}"
        names.append(name)
        lines.append(f"  - name: {name}")
        lines.append(f"    type: {'http' if p.protocol == 'http' else 'socks5'}")
        lines.append(f"    server: {p.ip}")
        lines.append(f"    port: {p.port}")
        if p.username:
            lines.append(f"    username: {p.username}")
            lines.append(f"    password: {p.password}")
    lines.append("proxy-groups:")
    lines.append("  - name: PROXYZ")
    lines.append("    type: url-test")
    lines.append("    url: http://www.gstatic.com/generate_204")
    lines.append("    interval: 300")
    lines.append("    proxies:")
    for n in names:
        lines.append(f"      - {n}")
    return "\n".join(lines) + "\n"


def export_clash(proxies: list[Proxy], path: str) -> str:
    """Clash YAML: tiap proxy jadi entri + satu grup `PROXYZ` (url-test).
    Hanya HTTP & SOCKS5 yang didukung Clash (SOCKS4 dilewati)."""
    return _atomic(path, clash_yaml(proxies))


def backup_existing(path: str, keep: int = 5) -> str | None:
    """Bila file sudah ada, salin ke output/backup/<nama>-<waktu>.<ext>
    dan jaga maksimal `keep` backup terbaru. Kembalikan path backup."""
    if not os.path.exists(path):
        return None
    from datetime import datetime
    bak_dir = os.path.join(os.path.dirname(path), "backup")
    os.makedirs(bak_dir, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(path))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(bak_dir, f"{base}-{stamp}{ext}")
    n = 1
    while os.path.exists(bak):
        n += 1
        bak = os.path.join(bak_dir, f"{base}-{stamp}-{n}{ext}")
    import shutil
    shutil.copy2(path, bak)
    olds = sorted(os.path.join(bak_dir, f) for f in os.listdir(bak_dir)
                  if f.startswith(base + "-"))
    for old in olds[:-keep]:
        try:
            os.remove(old)
        except OSError:
            pass
    return bak


def export_all(proxies: list[Proxy], out_dir: str) -> dict[str, str]:
    """Ekspor ke semua format. File lama di-backup dulu (maks 5).
    Kembalikan {format: path}."""
    targets = {
        "txt": os.path.join(out_dir, "proxy_hidup.txt"),
        "json": os.path.join(out_dir, "proxy_hidup.json"),
        "csv": os.path.join(out_dir, "proxy_hidup.csv"),
        "clash": os.path.join(out_dir, "proxy_clash.yaml"),
    }
    for path in targets.values():
        backup_existing(path)
    return {
        "txt": export_txt(proxies, targets["txt"]),
        "json": export_json(proxies, targets["json"]),
        "csv": export_csv(proxies, targets["csv"]),
        "clash": export_clash(proxies, targets["clash"]),
    }
