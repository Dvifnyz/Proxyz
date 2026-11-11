"""Proxyz — gateway: forward proxy lokal berputar + REST API + dashboard.

Perbedaan dari repo asli (core/server.py, 2.562 baris, 70% HTML):
- Satu jalur socket terpadu untuk SEMUA upstream (HTTP dan SOCKS4/5,
  dengan/tanpa auth) — tidak ada lagi jalur socket mentah terpisah yang
  tidak menangani POST/PUT/DELETE.
- Forward POST/PUT/DELETE/PATCH juga diteruskan (asli hanya GET/CONNECT).
- Token opsional (env PROXYZ_TOKEN): bila diisi, API + pemakaian proxy
  wajib bawa token — asli tanpa autentikasi sama sekali.
- Dashboard dipisah dan ringkas (bukan 1.795 baris HTML inline).
- Healer paralel (bukan sequential 1-per-1) + evict berbasis skor pool.

Cara pakai: python -m proxyz gateway --port 8888
  curl -x http://127.0.0.1:8888 http://api.ipify.org
  curl http://127.0.0.1:8888/api/status
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import re
import select
import socket
import ssl
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .models import Proxy
from .pool import Pool

HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate",
               "proxy-authorization", "te", "trailer", "transfer-encoding",
               "upgrade", "proxy-connection"}
SENSITIVE_HEADERS = {"x-forwarded-for", "via", "x-real-ip", "cf-connecting-ip"}
BOT_UA = ("python-requests", "aiohttp", "curl", "urllib", "httpx", "python-urllib")
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "output")


# ------------------------------------------------------------------ upstream
def _read_headers(sock: socket.socket, timeout: float = 10.0) -> bytes:
    sock.settimeout(timeout)
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf


def connect_via_proxy(upstream: Proxy, host: str, port: int,
                      timeout: float = 10.0) -> socket.socket:
    """Buka socket ke target (host:port) LEWAT satu upstream proxy.
    Mendukung HTTP (CONNECT + Proxy-Authorization), SOCKS5 (auth opsional),
    dan SOCKS4. Raises OSError bila gagal."""
    s = socket.create_connection((upstream.ip, upstream.port), timeout=timeout)
    try:
        if upstream.protocol == "http":
            lines = [f"CONNECT {host}:{port} HTTP/1.1",
                     f"Host: {host}:{port}"]
            if upstream.username:
                cred = base64.b64encode(
                    f"{upstream.username}:{upstream.password}".encode()).decode()
                lines.append(f"Proxy-Authorization: Basic {cred}")
            lines += ["Proxy-Connection: keep-alive", "", ""]
            s.sendall("\r\n".join(lines).encode())
            head = _read_headers(s, timeout)
            if b" 200" not in head.split(b"\r\n", 1)[0]:
                raise OSError(f"HTTP proxy menolak CONNECT: {head[:80]!r}")
            return s
        if upstream.protocol == "socks5":
            methods = b"\x05\x02\x00\x02" if upstream.username else b"\x05\x01\x00"
            s.sendall(methods)
            resp = s.recv(2)
            if len(resp) < 2 or resp[0] != 5:
                raise OSError("SOCKS5: greeting gagal")
            if resp[1] == 0x02:  # user/pass
                u, p = upstream.username.encode(), upstream.password.encode()
                s.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
                auth = s.recv(2)
                if len(auth) < 2 or auth[1] != 0:
                    raise OSError("SOCKS5: auth gagal")
            elif resp[1] != 0x00:
                raise OSError("SOCKS5: metode tidak didukung")
            req = (b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode()
                   + port.to_bytes(2, "big"))
            s.sendall(req)
            head = s.recv(4)
            if len(head) < 4 or head[1] != 0x00:
                raise OSError("SOCKS5: CONNECT ditolak")
            atyp = head[3]
            if atyp == 1:
                s.recv(4 + 2)
            elif atyp == 3:
                n = s.recv(1)[0]
                s.recv(n + 2)
            elif atyp == 4:
                s.recv(16 + 2)
            return s
        if upstream.protocol == "socks4":
            ip = socket.gethostbyname(host)
            pkt = (b"\x04\x01" + port.to_bytes(2, "big")
                   + bytes(map(int, ip.split("."))) + b"\x00")
            s.sendall(pkt)
            resp = s.recv(8)
            if len(resp) < 8 or resp[1] != 0x5A:
                raise OSError("SOCKS4: CONNECT ditolak")
            return s
        raise OSError(f"protokol tidak dikenal: {upstream.protocol}")
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        raise


# ------------------------------------------------------------------ healer
def _audit(audit_path: str | None, event: str, detail: dict | None = None) -> None:
    """Satu baris JSON ke file audit (bila diaktifkan). Gagal tulis = diam."""
    if not audit_path:
        return
    try:
        from datetime import datetime, timezone
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event}
        if detail:
            rec.update(detail)
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def start_healer(pool: Pool, interval: int = 90, min_healthy: int = 5,
                 target: int = 10, refill_fn=None, stop_event: threading.Event | None = None,
                 audit_path: str | None = None):
    """Thread daemon: probe pool paralel (TCP 2 dtk), buang yang mati,
    isi ulang bila di bawah ambang (cooldown refill 60 dtk)."""
    import concurrent.futures
    stop = stop_event or threading.Event()
    last_refill = 0.0

    def probe(p: Proxy) -> str | None:
        """Mati = kembalikan hostport. HTTP dicek BENAR-BENAR (GET ipify
        lewat proxy, timeout 4 dtk) — bukan cuma port kebuka, karena
        port kebuka belum tentu proxy-nya masih melayani request.
        SOCKS dicek via TCP (cek HTTP penuh sudah dilakukan checker)."""
        if p.protocol == "http":
            try:
                h = urllib.request.ProxyHandler(
                    {"http": p.url, "https": p.url})  # p.url sudah berisi skema
                opener = urllib.request.build_opener(h)
                req = urllib.request.Request(
                    "http://api.ipify.org",
                    headers={"User-Agent": "Proxyz/1.0"})
                with opener.open(req, timeout=4) as r:
                    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+",
                                    r.read().decode().strip() or ""):
                        return None
            except Exception:
                return p.hostport
            return p.hostport
        try:
            with socket.create_connection((p.ip, p.port), timeout=2):
                return None
        except Exception:
            return p.hostport

    def loop():
        nonlocal last_refill
        while not stop.wait(interval):
            snap = pool.snapshot()
            if not snap:
                continue
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
                dead = [d for d in ex.map(probe, snap) if d]
            if dead:
                pool.prune(dead)
                _audit(audit_path, "healer_prune", {"dead": dead, "pool": len(pool)})
            if len(pool) < min_healthy and refill_fn and time.time() - last_refill > 60:
                last_refill = time.time()
                try:
                    fresh = refill_fn(target=target)
                    if fresh:
                        pool.add(fresh)
                        _audit(audit_path, "healer_refill",
                               {"added": len(fresh), "pool": len(pool)})
                except Exception:
                    pass

    t = threading.Thread(target=loop, daemon=True, name="proxyz-healer")
    t.start()
    return stop


# ------------------------------------------------------------------ muat pool
def load_pool_from_disk() -> list[Proxy]:
    """Baca pool dari hasil panen terakhir + manual + webshare (bila ada key).
    Urutan: residential dulu (webshare/manual ber-auth), lalu hasil panen."""
    out: list[Proxy] = []
    seen: set[str] = set()

    def _add(p: Proxy):
        if p.hostport not in seen:
            seen.add(p.hostport)
            out.append(p)

    # 1. Webshare via API resmi (semua akun, bila key tersedia)
    try:
        from .residential import fetch_all_webshare, load_manual
        for p in fetch_all_webshare():
            _add(p)
        for p in load_manual():
            _add(p)
    except Exception:
        pass
    # 2. Hasil panen terakhir
    jpath = os.path.join(OUT_DIR, "proxy_hidup.json")
    if os.path.exists(jpath):
        try:
            with open(jpath, encoding="utf-8") as f:
                for row in json.load(f):
                    p = Proxy(protocol=row.get("protocol", "http"), ip=row["ip"],
                              port=int(row["port"]), score=int(row.get("score") or 0),
                              anonymity=row.get("anonymity", ""),
                              country_code=row.get("country_code", ""),
                              ms=row.get("ms"), source="panen")
                    _add(p)
        except Exception:
            pass
    tpath = os.path.join(OUT_DIR, "proxy_hidup.txt")
    if os.path.exists(tpath):
        try:
            with open(tpath, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    p = Proxy.from_string(line, source="panen")
                    if p:
                        _add(p)
        except Exception:
            pass
    return out


# ------------------------------------------------------------------ HTTP API
DASHBOARD_HTML = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<title>Proxyz — Gateway</title><style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:2em auto;padding:0 1em}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}
button{padding:6px 12px;margin-right:6px;cursor:pointer}
</style></head><body>
<h1>⚡ Proxyz Gateway</h1>
<p id="stats">memuat…</p>
<p id="leak">Leak test: belum dijalankan.</p>
<p><button onclick="aksi('rotate')">🔄 Rotasi</button>
<button onclick="aksi('refill')">🌾 Isi ulang</button>
<button onclick="leak()">🕵️ Tes kebocoran IP</button>
<button onclick="bench()">⚡ Uji kecepatan (top 5)</button>
<button onclick="muat()">↻ Refresh</button></p>
<p id="bench"></p>
<p>Pakai: <code>curl -x http://127.0.0.1:8888 http://api.ipify.org</code> ·
<a href="/api/status">/api/status</a> · <a href="/api/proxies">/api/proxies</a> ·
<a href="/api/leak-test">/api/leak-test</a> · <a href="/api/bench">/api/bench</a> ·
<a href="/metrics">/metrics</a> · <a href="/proxy.pac">/proxy.pac</a></p>
<table><thead><tr><th>Proxy</th><th>Protokol</th><th>Skor</th><th>Anonimitas</th><th>Negara</th><th>Latency</th></tr></thead>
<tbody id="rows"></tbody></table>
<script>
async function muat(){
  const s = await (await fetch('/api/status')).json();
  document.getElementById('stats').textContent =
    `Pool: ${s.pool} proxy (${s.http} HTTP, ${s.socks5} SOCKS5, ${s.residential} residential) | ` +
    `request: ${s.total_requests} (${s.success_pct}% sukses) | uptime: ${s.uptime_sec} dtk`;
  const list = await (await fetch('/api/proxies')).json();
  document.getElementById('rows').innerHTML = list.map(p => {
    const warna = p.score >= 80 ? 'green' : p.score < 50 ? 'red' : 'inherit';
    return `<tr><td>${p.proxy}</td><td>${p.protocol}</td><td style="color:${warna};font-weight:bold">${p.score}</td><td>${p.anonymity||'-'}</td><td>${p.country_code||'-'}</td><td>${p.ms??'-'} ms</td></tr>`;
  }).join('');
}
async function aksi(n){ await fetch('/api/'+n); muat(); }
async function leak(){
  document.getElementById('leak').textContent = 'Tes kebocoran IP…';
  const r = await (await fetch('/api/leak-test')).json();
  document.getElementById('leak').textContent =
    r.zero_leak ? `✅ ZERO LEAK — IP asli ${r.direct_ip}, IP via gateway ${r.gateway_ip}` :
    `⚠️ IP asli ${r.direct_ip||'-'} vs gateway ${r.gateway_ip||'-'} — periksa pool`;
}
async function bench(){
  document.getElementById('bench').textContent = 'Uji kecepatan… (unduh 1 MB per proxy)';
  const list = await (await fetch('/api/bench?jumlah=5')).json();
  document.getElementById('bench').innerHTML = '<b>Tercepat:</b><br>' +
    list.map((r,i) => r.ok ? `${i+1}. ${r.proxy} — ${r.kbps} KB/detik (${r.seconds} dtk)` :
      `${r.proxy} — gagal: ${r.error}`).join('<br>');
}
muat(); setInterval(muat, 5000);
</script></body></html>"""


def make_handler(pool: Pool, token: str = "", refill_fn=None,
                 rate_limit_per_min: int = 0, audit_path: str | None = None):
    # Rate limit per IP untuk /api/* (token bucket sederhana, jendela 60 dtk).
    # 0 = tidak dibatasi. Forward proxy TIDAK di-rate-limit (itu produknya).
    _rl: dict[str, list] = {}
    _rl_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        # -- util --
        def _rate_limited(self) -> tuple[bool, int]:
            if not rate_limit_per_min:
                return False, 0
            ip = self.client_address[0]
            now = time.time()
            with _rl_lock:
                window, count = _rl.get(ip, (now, 0))
                if now - window >= 60:
                    window, count = now, 0
                if count >= rate_limit_per_min:
                    return True, int(60 - (now - window)) + 1
                _rl[ip] = (window, count + 1)
            return False, 0

        def _token_ok(self) -> bool:
            if not token:
                return True
            auth = self.headers.get("Authorization", "")
            if auth == f"Bearer {token}":
                return True
            if self.headers.get("X-Proxyz-Token") == token:
                return True
            if self.headers.get("X-Proxyx-Token") == token:  # header lama (v2.x)
                return True
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return q.get("token", [""])[0] == token

        def _send(self, code: int, body: bytes, ctype: str = "application/json"):
            try:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                pass

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj).encode(), "application/json")

        def _session_country(self):
            sid = (self.headers.get("X-Session-ID")
                   or self.headers.get("X-Sticky-Session"))
            if not sid:
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                sid = (q.get("session") or q.get("session_id") or [None])[0]
            country = self.headers.get("X-Country")
            return sid, country

        def _leak_test(self) -> dict:
            """Bandingkan IP langsung vs IP lewat gateway (1 proxy pool).
            zero_leak=True bila keduanya ada, berbeda, dan IP gateway valid.
            ipify asli mengembalikan IP polos; standin tes mengembalikan
            JSON {"ip": ...} — keduanya diterima."""
            def _ip(text: str) -> str:
                text = (text or "").strip()
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and isinstance(data.get("ip"), str):
                        text = data["ip"]
                except Exception:
                    pass
                m = re.fullmatch(r"\d+\.\d+\.\d+\.\d+", text)
                return text if m else ""

            direct, gw_ip = "", ""
            try:
                req = urllib.request.Request(
                    "http://api.ipify.org", headers={"User-Agent": "Proxyz/1.0"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    direct = _ip(r.read().decode())
            except Exception:
                pass
            up = pool.next()
            if up:
                try:
                    h = urllib.request.ProxyHandler({"http": up.url, "https": up.url})
                    opener = urllib.request.build_opener(h)
                    req = urllib.request.Request(
                        "http://api.ipify.org", headers={"User-Agent": "Proxyz/1.0"})
                    with opener.open(req, timeout=10) as r:
                        gw_ip = _ip(r.read().decode())
                except Exception:
                    pass
            ok = bool(direct and gw_ip and direct != gw_ip)
            return {"direct_ip": direct, "gateway_ip": gw_ip, "zero_leak": ok}

        # -- API --
        def _handle_api(self) -> bool:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/"):
                limited, retry = self._rate_limited()
                if limited:
                    self._json(429, {"error": "rate limit", "retry_after": retry})
                    return True
            if path in ("/", "/dashboard", "/gui", "/ui"):
                if path == "/" and "text/html" not in (self.headers.get("Accept") or ""):
                    self._json(200, {**pool.stats(), "endpoints": [
                        "/api/status", "/api/proxies", "/api/random",
                        "/api/rotate", "/api/refill", "/api/leak-test",
                        "/api/bench", "/api/clash.yaml", "/metrics", "/proxy.pac"]})
                else:
                    self._send(200, DASHBOARD_HTML.encode(), "text/html; charset=utf-8")
                return True
            if not self._token_ok():
                self._json(401, {"error": "token dibutuhkan (env PROXYZ_TOKEN)"})
                return True
            if path == "/api/status" or path == "/api/stats":
                self._json(200, pool.stats())
            elif path == "/api/proxies" or path == "/api/all":
                self._json(200, [p.to_dict() for p in pool.snapshot()])
            elif path == "/api/random":
                p = pool.next()
                self._json(200, p.to_dict() if p else {})
            elif path == "/api/rotate":
                p = pool.force_rotate()
                _audit(audit_path, "api_rotate",
                       {"client": self.client_address[0],
                        "proxy": p.hostport if p else None})
                self._json(200, p.to_dict() if p else {})
            elif path == "/api/refill":
                if refill_fn:
                    threading.Thread(target=lambda: pool.add(refill_fn(target=10) or []),
                                     daemon=True).start()
                    _audit(audit_path, "api_refill",
                           {"client": self.client_address[0]})
                    self._json(200, {"status": "refill dimulai"})
                else:
                    self._json(200, {"status": "tidak ada refill_fn"})
            elif path == "/metrics":
                s = pool.stats()
                txt = ("# Proxyz metrics\n"
                       f"proxyz_pool_size {s['pool']}\n"
                       f"proxyz_requests_total {s['total_requests']}\n"
                       f"proxyz_requests_success {s['success_requests']}\n"
                       f"proxyz_requests_failed {s['failed_requests']}\n"
                       f"proxyz_evicted_total {s['evicted']}\n")
                self._send(200, txt.encode(), "text/plain")
            elif path == "/api/leak-test":
                self._json(200, self._leak_test())
            elif path == "/api/bench":
                from .bench import bench_pool
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    n = max(1, min(10, int((q.get("jumlah") or ["5"])[0])))
                except ValueError:
                    n = 5
                snap = pool.snapshot()[:n]
                self._json(200, bench_pool(snap))
            elif path == "/api/clash.yaml":
                from .exporter import clash_yaml
                self._send(200, clash_yaml(pool.snapshot()).encode(), "text/yaml")
            elif path == "/api/report":
                from .harvester import health_report
                from .report import build_report, load_bench_results
                self._json(200, build_report(pool.snapshot(), health_report(),
                                             load_bench_results(), pool.stats()))
            elif path in ("/proxy.pac", "/pac", "/wpad.dat"):
                port = self.server.server_address[1]
                pac = (f'function FindProxyForURL(url, host) {{ '
                       f'return "PROXY 127.0.0.1:{port}"; }}\n')
                self._send(200, pac.encode(), "application/x-ns-proxy-autoconfig")
            else:
                return False
            return True

        # -- proxy --
        def _pick(self):
            if token:  # token gateway: Bearer di Proxy-Authorization
                pa = self.headers.get("Proxy-Authorization", "")
                if pa.startswith("Bearer "):
                    if pa[7:].strip() != token:
                        return None
                else:
                    return None
            sid, country = self._session_country()
            return pool.next(session_id=sid, country=country)

        def _forward(self):
            up = self._pick()
            if up is None:
                if token:
                    self._json(407, {"error": "butuh Proxy-Authorization: Bearer <token>"})
                else:
                    self._json(502, {"error": "pool kosong — panen dulu"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            url = self.path
            if not url.startswith("http"):
                host = self.headers.get("Host", "")
                url = f"http://{host}{self.path}"
            parts = urllib.parse.urlparse(url)
            is_https = parts.scheme == "https"
            target_host, target_port = parts.hostname or "", parts.port or (443 if is_https else 80)
            path_q = parts.path or "/"
            if parts.query:
                path_q += "?" + parts.query
            for _ in range(3):
                try:
                    # Target HTTP polos lewat proxy HTTP = GET absolute-URI
                    # TANPA CONNECT (CONNECT hanya untuk terowongan/TLS).
                    # Proxy HTTP sederhana tidak melayani CONNECT ke :80.
                    if not is_https and up.protocol == "http":
                        sock = socket.create_connection((up.ip, up.port), timeout=10)
                        request_target = url  # absolute URI
                        extra_auth = []
                        if up.username:
                            cred = base64.b64encode(
                                f"{up.username}:{up.password}".encode()).decode()
                            extra_auth.append(("Proxy-Authorization", f"Basic {cred}"))
                    else:
                        sock = connect_via_proxy(up, target_host, target_port, timeout=10)
                        request_target = path_q
                        extra_auth = []
                        if is_https:
                            ctx = ssl.create_default_context()
                            sock = ctx.wrap_socket(sock, server_hostname=target_host)
                    # kirim request mentah
                    headers = self._sanitized_headers(target_host) + extra_auth
                    req_lines = [f"{self.command} {request_target} HTTP/1.1"]
                    for k, v in headers:
                        req_lines.append(f"{k}: {v}")
                    req_lines += ["Connection: close", "", ""]
                    sock.sendall("\r\n".join(req_lines).encode("latin-1"))
                    if body:
                        sock.sendall(body)
                    resp = http.client.HTTPResponse(sock, method=self.command)
                    resp.begin()
                    data = resp.read()
                    self._reply(resp.status, resp.getheaders(), data)
                    resp.close()
                    pool.mark_success(up)
                    return
                except Exception:
                    pool.mark_failed(up)
                    up = pool.next()
                    if up is None:
                        break
            self._json(502, {"error": "semua proxy dicoba gagal — panen ulang"})

        def _sanitized_headers(self, host: str):
            out = []
            ua = self.headers.get("User-Agent", "")
            if any(b in ua.lower() for b in BOT_UA) or not ua:
                ua = BROWSER_UA
            for k, v in self.headers.items():
                kl = k.lower()
                if kl in HOP_HEADERS or kl in SENSITIVE_HEADERS or kl == "host":
                    continue
                if kl == "user-agent":
                    continue
                out.append((k, v))
            out.insert(0, ("Host", host))
            out.insert(1, ("User-Agent", ua))
            return out

        def _reply(self, status: int, headers, data: bytes):
            try:
                self.send_response(status)
                for k, v in headers:
                    if k.lower() in HOP_HEADERS or k.lower() == "content-length":
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                pass
            finally:
                self.close_connection = True

        def do_GET(self):
            if self.path.startswith("/api/") or self.path in ("/", "/dashboard", "/gui", "/ui",
                                                              "/metrics", "/proxy.pac", "/pac", "/wpad.dat"):
                if not self._handle_api():
                    self._json(404, {"error": "tidak dikenal"})
                return
            self._forward()

        def do_POST(self):
            self._forward()

        def do_PUT(self):
            self._forward()

        def do_DELETE(self):
            self._forward()

        def do_PATCH(self):
            self._forward()

        def do_CONNECT(self):
            up = self._pick()
            if up is None:
                self.send_error(502, "pool kosong / token salah")
                return
            host_port = self.path
            host, _, port = host_port.rpartition(":")
            for _ in range(3):
                try:
                    sock = connect_via_proxy(up, host, int(port or 443), timeout=10)
                    self.send_response(200, "Connection Established")
                    self.end_headers()
                    pool.mark_success(up)
                    self._relay(self.connection, sock)
                    return
                except Exception:
                    pool.mark_failed(up)
                    up = pool.next()
                    if up is None:
                        break
            try:
                self.send_error(502, "CONNECT gagal di semua proxy")
            except Exception:
                pass

        def _relay(self, a, b):
            def pump(src, dst):
                try:
                    while True:
                        data = src.recv(8192)
                        if not data:
                            break
                        dst.sendall(data)
                except Exception:
                    pass
                finally:
                    try:
                        dst.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
            t1 = threading.Thread(target=pump, args=(a, b), daemon=True)
            t2 = threading.Thread(target=pump, args=(b, a), daemon=True)
            t1.start(); t2.start()
            t1.join(); t2.join()
            for s in (a, b):
                try:
                    s.close()
                except Exception:
                    pass
    return Handler


def _pump(src: socket.socket, dst: socket.socket) -> None:
    """Teruskan byte satu arah sampai EOF (dipakai relay SOCKS5)."""
    try:
        while True:
            chunk = src.recv(65536)
            if not chunk:
                break
            dst.sendall(chunk)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def serve_socks5(pool: Pool, port: int,
                 stop_event: threading.Event | None = None) -> threading.Event:
    """Listener SOCKS5 (tanpa auth) yang meneruskan tiap koneksi lewat
    satu proxy dari pool (HTTP/SOCKS4/SOCKS5 upstream). BIND dan UDP
    ASSOCIATE ditolak (0x07) — hanya CONNECT yang didukung.
    Berjalan di thread daemon; kembalikan event untuk menghentikannya."""
    import socketserver

    stop = stop_event or threading.Event()

    class Socks5Handler(socketserver.BaseRequestHandler):
        def handle(self):
            conn = self.request
            conn.settimeout(30)
            try:
                head = conn.recv(2)
                if len(head) < 2 or head[0] != 0x05:
                    return
                nmethods = head[1]
                conn.recv(nmethods)  # metode yang ditawarkan klien
                conn.sendall(b"\x05\x00")  # no auth
                req = conn.recv(4)
                if len(req) < 4 or req[0] != 0x05:
                    return
                cmd, atyp = req[1], req[3]
                if cmd != 0x01:
                    conn.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                    return
                if atyp == 0x01:
                    raw = conn.recv(4)
                    host = socket.inet_ntoa(raw)
                elif atyp == 0x03:
                    n = conn.recv(1)[0]
                    host = conn.recv(n).decode(errors="ignore")
                elif atyp == 0x04:
                    raw = conn.recv(16)
                    host = socket.inet_ntop(socket.AF_INET6, raw)
                else:
                    conn.sendall(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
                    return
                dport = int.from_bytes(conn.recv(2), "big")
                up = pool.next()
                if up is None:
                    conn.sendall(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
                    return
                try:
                    upstream_sock = connect_via_proxy(up, host, dport, timeout=15)
                except Exception:
                    pool.mark_failed(up)
                    conn.sendall(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
                    return
                pool.mark_success(up)
                conn.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
                t1 = threading.Thread(target=_pump, args=(conn, upstream_sock), daemon=True)
                t2 = threading.Thread(target=_pump, args=(upstream_sock, conn), daemon=True)
                t1.start(); t2.start()
                t1.join(); t2.join()
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    srv = Server(("127.0.0.1", port), Socks5Handler)

    def _run():
        srv.timeout = 0.5
        while not stop.is_set():
            srv.handle_request()

    threading.Thread(target=_run, daemon=True, name="proxyz-socks5").start()
    print(f"  SOCKS5 jalan di 127.0.0.1:{port} (lewat pool gateway)")
    return stop


def serve(pool: Pool, port: int = 8888, token: str = "", refill_fn=None,
          healer: bool = True, healer_interval: int = 90,
          rate_limit_per_min: int = 60, audit_path: str | None = None,
          socks_port: int = 0):
    """Jalankan gateway (blocking). Token dari env PROXYZ_TOKEN bila ada
    (PROXYX_TOKEN lama tetap dibaca sebagai fallback)."""
    token = (token or os.environ.get("PROXYZ_TOKEN", "")
             or os.environ.get("PROXYX_TOKEN", ""))
    handler = make_handler(pool, token=token, refill_fn=refill_fn,
                           rate_limit_per_min=rate_limit_per_min,
                           audit_path=audit_path)
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    stop = None
    if healer:
        stop = start_healer(pool, interval=healer_interval, refill_fn=refill_fn,
                            audit_path=audit_path)
    socks_stop = None
    if socks_port:
        socks_stop = serve_socks5(pool, socks_port)
    print(f"  Gateway jalan di http://127.0.0.1:{port} "
          f"({len(pool)} proxy, token={'ON' if token else 'OFF'}, "
          f"rate-limit {rate_limit_per_min}/mnt"
          f"{', SOCKS5 :' + str(socks_port) if socks_port else ''})")
    print(f"  Tes: curl -x http://127.0.0.1:{port} http://api.ipify.org")
    print(f"  Dashboard: http://127.0.0.1:{port}/dashboard   (Ctrl+C berhenti)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Gateway berhenti.")
    finally:
        if stop:
            stop.set()
        if socks_stop:
            socks_stop.set()
        srv.server_close()
    return srv
