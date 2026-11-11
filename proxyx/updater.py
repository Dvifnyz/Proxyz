"""Proxyx — updater AMAN.

Repo asli: `perform_update` menjalankan `git pull`, lalu fallback
`git reset --hard origin/master` (menghapus perubahan lokal pengguna),
kemudian mengeksekusi `auto_run_commands` dari version.json REMOTE
via shell=True — siapa pun yang menguasai repo bisa menjalankan
perintah arbitrer di mesin pengguna.

Proxyx tidak melakukan satu pun dari itu:
- Cek versi hanya MEMBACA GitHub Releases API (tidak mengeksekusi apa pun).
- Update dilakukan via `pip install --upgrade` dari tag release
  (tanpa shell=True, tanpa git reset, tanpa perintah remote),
  dan HANYA setelah pengguna mengetik 'y' secara eksplisit.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request

RELEASES_API = "https://api.github.com/repos/Dvifnyz/Proxyz/releases/latest"
UA = {"User-Agent": "Proxyx/1.0"}


def _parse_version(tag: str) -> tuple[int, ...]:
    tag = tag.strip().lstrip("vV")
    parts = []
    for chunk in tag.split("."):
        num = "".join(c for c in chunk if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts) or (0,)


TAGS_API = "https://api.github.com/repos/Dvifnyz/Proxyz/tags"


def _get_json(url: str, timeout: float):
    req = urllib.request.Request(url, headers={**UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def check_update(current: str, timeout: float = 10.0) -> dict:
    """Cek rilis terbaru di GitHub. Tidak mengeksekusi apa pun.
    Bila belum ada Release (API 404), fallback ke daftar tag."""
    try:
        data = _get_json(RELEASES_API, timeout)
        latest = str(data.get("tag_name", "")).strip()
        url = data.get("html_url", "")
        notes = str(data.get("body", ""))[:500]
    except Exception:
        try:
            tags = _get_json(TAGS_API, timeout)
            latest = str(tags[0].get("name", "")).strip() if tags else ""
            url = f"https://github.com/Dvifnyz/Proxyz/releases/tag/{latest}" if latest else ""
            notes = ""
        except Exception as e:
            return {"current": current, "latest": "", "update_available": False,
                    "error": f"tidak bisa menghubungi GitHub: {e}"}
    if not latest:
        return {"current": current, "latest": "", "update_available": False,
                "error": "tidak ada rilis/tag di GitHub"}
    return {"current": current, "latest": latest,
            "update_available": _parse_version(latest) > _parse_version(current),
            "url": url, "notes": notes}


def update_via_pip(tag: str) -> tuple[bool, str]:
    """Update via pip dari tag release. Tanpa shell, tanpa git."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade",
           f"git+https://github.com/Dvifnyz/Proxyz.git@{tag}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        return False, str(e)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-500:]
        return False, f"pip gagal (exit {proc.returncode}): {tail}"
    return True, f"Proxyx diperbarui ke {tag}. Jalankan ulang gateway bila sedang jalan."
