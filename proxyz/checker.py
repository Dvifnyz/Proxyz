"""Proxyz — checker: uji proxy hidup + anonimitas + geo + skor.

Satu mesin cek (repo asli punya tiga jalur yang saling duplikat).
- HTTP  : request beneran lewat proxy ke api.ipify.org (HTTPS).
- SOCKS5/4: handshake SOCKS mentah via asyncio (tanpa aiohttp-socks),
  lalu GET / ke api.ipify.org:80 lewat terowongan itu.
- Anonimitas mengikuti logika teruji repo asli (checker.py):
  elite = IP asli tidak bocor & tidak ada header jejak proxy.
- Skor 0-100: anonimitas + latency. Dipakai gateway untuk urutan pool.
- Geo: batch ip-api.com/batch (maks 100 IP/request), HANYA bila diminta —
  jangan lookup per proxy (rate-limit 45/menit di tier gratis).
"""
from __future__ import annotations

import asyncio
import json
import re
import ssl
import time
import urllib.request

from .models import Proxy

TEST_URL = "https://api.ipify.org?format=json"
TEST_HOST = "api.ipify.org"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Proxyz/1.0"}
IP_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
VIA_HEADERS = ("via", "x-forwarded-for", "forwarded", "x-real-ip",
               "proxy-connection", "x-proxy-id", "x-cache")

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore
    HAS_AIOHTTP = False


# ------------------------------------------------------------------ murni
def classify_anonymity(egress_ip: str, host_ip: str, headers: dict) -> str:
    """elite / anonymous / transparent — logika dari repo asli, dipertahankan
    karena sudah benar: bocor IP = transparent, ada jejak header = anonymous."""
    h = {k.lower(): str(v) for k, v in (headers or {}).items()}
    if egress_ip == host_ip or (host_ip and host_ip in " ".join(h.values())):
        return "transparent"
    if any(k in h for k in VIA_HEADERS):
        return "anonymous"
    return "elite"


def score_proxy(anonymity: str, ms: int | None) -> int:
    """Skor 0-100: elite mulai 95, anonymous 80, transparent 45, tcp-ok 55.
    Latency memotong sampai -30 (tiap 100 ms di atas 300 ms = -2)."""
    base = {"elite": 95, "anonymous": 80, "transparent": 45, "tcp-ok": 55}.get(anonymity, 0)
    if ms is None:
        return base
    penalty = max(0, (ms - 300) // 100) * 2
    return max(0, min(100, base - min(penalty, 30)))


def get_host_ip(timeout: float = 5.0) -> str:
    """IP asli mesin ini (tanpa proxy), dicoba dari 2 layanan."""
    for url in ("https://api.ipify.org", "https://icanhazip.com"):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ip = r.read().decode().strip()
            if IP_RE.match(ip):
                return ip
        except Exception:
            continue
    return ""


# ------------------------------------------------------------------ HTTP
async def check_http(proxy: Proxy, host_ip: str, timeout: float = 5.0,
                     test_url: str = TEST_URL) -> Proxy | None:
    """Cek HTTP via aiohttp. Kembalikan Proxy terisi (ms/anonymity/score)
    atau None bila mati. Timeout bertingkat: connect 2 dtk, total `timeout`.
    `test_url` hanya untuk tes (default HTTPS — via proxy aiohttp memakai
    CONNECT, itu perilaku benar untuk HTTPS)."""
    if not HAS_AIOHTTP:
        return None
    start = time.perf_counter()
    ctx = ssl.create_default_context()
    conn = aiohttp.TCPConnector(ssl=ctx, limit=0)
    to = aiohttp.ClientTimeout(total=timeout, connect=2.0)
    try:
        async with aiohttp.ClientSession(headers=UA, connector=conn, timeout=to,
                                         trust_env=True) as s:
            async with s.get(test_url, proxy=proxy.url) as r:
                if r.status != 200:
                    return None
                data = await r.json(content_type=None)
                egress = str(data.get("ip", "")).strip()
                if not IP_RE.match(egress):
                    return None
                headers = dict(r.headers)
    except Exception:
        return None
    finally:
        await conn.close()
    ms = int((time.perf_counter() - start) * 1000)
    proxy.ms = ms
    proxy.egress_ip = egress
    proxy.anonymity = classify_anonymity(egress, host_ip, headers)
    proxy.score = score_proxy(proxy.anonymity, ms)
    return proxy


# ------------------------------------------------------------------ SOCKS
async def _socks5_handshake(reader, writer, host: str, port: int) -> bool:
    """Handshake SOCKS5 tanpa auth, lalu CONNECT ke host:port. True = terowongan siap."""
    writer.write(b"\x05\x01\x00")
    await writer.drain()
    resp = await asyncio.wait_for(reader.readexactly(2), timeout=5)
    if resp != b"\x05\x00":
        return False
    req = b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + port.to_bytes(2, "big")
    writer.write(req)
    await writer.drain()
    resp = await asyncio.wait_for(reader.readexactly(4), timeout=5)
    if len(resp) < 4 or resp[1] != 0x00:
        return False
    atyp = resp[3]
    n = {1: 4, 3: None, 4: 16}.get(atyp)
    if n is None:
        ln = await asyncio.wait_for(reader.readexactly(1), timeout=5)
        n = ln[0]
    await asyncio.wait_for(reader.readexactly(n + 2), timeout=5)
    return True


async def _socks4_handshake(reader, writer, host: str, port: int) -> bool:
    """SOCKS4 (tanpa auth): CONNECT + user-id kosong. IP target harus
    di-resolve lokal dulu (SOCKS4 tidak bawa hostname)."""
    import socket as _socket
    try:
        ip = _socket.gethostbyname(host)
    except Exception:
        return False
    pkt = b"\x04\x01" + port.to_bytes(2, "big") + bytes(map(int, ip.split("."))) + b"\x00"
    writer.write(pkt)
    await writer.drain()
    resp = await asyncio.wait_for(reader.readexactly(8), timeout=5)
    return len(resp) == 8 and resp[1] == 0x5A


async def check_socks(proxy: Proxy, host_ip: str, timeout: float = 6.0) -> Proxy | None:
    """Cek SOCKS4/5: buka terowongan ke api.ipify.org:80, kirim GET, baca IP.
    Tanpa library SOCKS tambahan — handshake ditulis sendiri."""
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(proxy.ip, proxy.port), timeout=3.0)
    except Exception:
        return None
    try:
        ok = await asyncio.wait_for(
            (_socks5_handshake if proxy.protocol == "socks5" else _socks4_handshake)(
                reader, writer, TEST_HOST, 80), timeout=timeout)
        if not ok:
            return None
        writer.write(b"GET / HTTP/1.1\r\nHost: api.ipify.org\r\n"
                     b"User-Agent: Proxyz/1.0\r\nConnection: close\r\n\r\n")
        await writer.drain()
        raw = await asyncio.wait_for(reader.read(-1), timeout=timeout)
        body = raw.split(b"\r\n\r\n", 1)[-1].decode(errors="ignore").strip()
        if not IP_RE.match(body):
            return None
    except Exception:
        return None
    finally:
        try:
            writer.close()
        except Exception:
            pass
    ms = int((time.perf_counter() - start) * 1000)
    proxy.ms = ms
    proxy.egress_ip = body
    # Lewat terowongan mentah tidak ada header respons proxy yang bisa dibaca,
    # jadi anonimitas dinilai dari kebocoran IP saja (elite bila IP beda).
    proxy.anonymity = "transparent" if body == host_ip else "elite"
    proxy.score = score_proxy(proxy.anonymity, ms)
    return proxy


async def check_one(proxy: Proxy, host_ip: str, timeout: float = 5.0,
                    test_url: str = TEST_URL) -> Proxy | None:
    if proxy.protocol == "http":
        return await check_http(proxy, host_ip, timeout, test_url)
    return await check_socks(proxy, host_ip, timeout + 1)


# ------------------------------------------------------------------ pool
async def check_pool(candidates: list[dict], target: int = 20,
                     max_check: int = 300, timeout: float = 5.0,
                     workers: int = 100) -> list[Proxy]:
    """Cek kandidat sampai dapat `target` yang hidup (berhenti lebih awal).
    Kandidat dari sumber segar sudah diurutkan duluan oleh harvester."""
    host_ip = await asyncio.to_thread(get_host_ip)
    sem = asyncio.Semaphore(workers)
    alive: list[Proxy] = []
    stop = asyncio.Event()

    async def _run(item: dict):
        if stop.is_set():
            return
        async with sem:
            if stop.is_set():
                return
            p = Proxy(protocol=item["protocol"], ip=item["ip"], port=item["port"],
                      source=item.get("source", ""))
            ok = await check_one(p, host_ip, timeout)
            if ok:
                alive.append(ok)
                if len(alive) >= target:
                    stop.set()

    await asyncio.gather(*[_run(c) for c in candidates[:max_check]])
    alive.sort(key=lambda p: -p.score)
    return alive


def check_pool_sync(*args, **kwargs) -> list[Proxy]:
    return asyncio.run(check_pool(*args, **kwargs))


# ------------------------------------------------------------------ geo
def enrich_geo(proxies: list[Proxy], timeout: float = 8.0) -> list[Proxy]:
    """Isi negara/kota/ISP via SATU request batch per 100 IP (ip-api.com).
    Gagal (rate-limit/offline) = lewati diam-diam, proxy tetap dipakai."""
    if not proxies:
        return proxies
    for i in range(0, len(proxies), 100):
        chunk = proxies[i:i + 100]
        try:
            payload = json.dumps([{"query": p.ip, "fields": "status,country,countryCode,city,isp,query"}
                                  for p in chunk]).encode()
            req = urllib.request.Request("http://ip-api.com/batch", data=payload,
                                         headers={"Content-Type": "application/json",
                                                  "User-Agent": "Proxyz/1.0"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                rows = json.loads(r.read().decode())
            by_ip = {row.get("query"): row for row in rows if row.get("status") == "success"}
            for p in chunk:
                row = by_ip.get(p.ip)
                if row:
                    p.country = row.get("country", "")
                    p.country_code = row.get("countryCode", "")
                    p.city = row.get("city", "")
                    p.isp = row.get("isp", "")
        except Exception:
            continue
    return proxies
