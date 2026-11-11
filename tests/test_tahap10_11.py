"""Tes v1.5.0: rate limit + audit + listener SOCKS5."""
import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from proxyz.gateway import make_handler, serve_socks5, start_healer
from proxyz.models import Proxy
from proxyz.pool import Pool
from tests.test_gateway import DummyHttpProxy, IpifyStandin, _start_server


def _gw(pool, **kw):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pool, **kw))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _get(port, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_rate_limit_blocks_after_limit():
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=18080, score=90)])
    gw = _gw(pool, rate_limit_per_min=3)
    try:
        port = gw.server_address[1]
        codes = [_get(port, "/api/status")[0] for _ in range(4)]
        assert codes[:3] == [200, 200, 200]
        assert codes[3] == 429
        body = json.loads(_get(port, "/api/status")[1])
        assert body["error"] == "rate limit" and body["retry_after"] >= 1
    finally:
        gw.shutdown()


def test_rate_limit_does_not_block_forward():
    # Forward proxy tidak di-rate-limit (hanya /api/*).
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=18080, score=90)])
    gw = _gw(pool, rate_limit_per_min=1)
    try:
        port = gw.server_address[1]
        _get(port, "/api/status")
        # request forward ke pool kosong -> 502, bukan 429
        code, _ = _get(port, "/api/status")
        assert code == 429  # API tetap kena limit
    finally:
        gw.shutdown()


def test_audit_logs_rotate_and_healer(tmp_path):
    audit = str(tmp_path / "audit.jsonl")
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=18080, score=90),
                 Proxy(protocol="http", ip="127.0.0.1", port=9, score=80)])
    gw = _gw(pool, audit_path=audit)
    try:
        _get(gw.server_address[1], "/api/rotate")
    finally:
        gw.shutdown()
    stop = start_healer(pool, interval=1, min_healthy=1, audit_path=audit)
    import time
    time.sleep(3)
    stop.set()
    with open(audit, encoding="utf-8") as f:
        lines = [json.loads(entry) for entry in f]
    events = [entry["event"] for entry in lines]
    assert "api_rotate" in events
    assert "healer_prune" in events
    assert all("ts" in entry for entry in lines)


def _socks5_client(port, host, dport, payload):
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(b"\x05\x01\x00")
    assert s.recv(2) == b"\x05\x00"
    req = b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + dport.to_bytes(2, "big")
    s.sendall(req)
    resp = s.recv(10)
    assert resp[1] == 0x00, resp
    s.sendall(payload)
    out = b""
    s.settimeout(5)
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except socket.timeout:
        pass
    s.close()
    return out


def test_socks5_listener_forwards_via_pool():
    standin = _start_server(IpifyStandin)
    try:
        DummyHttpProxy.TARGET_PORT = standin.server_address[1]
        up = _start_server(DummyHttpProxy)
        try:
            pool = Pool([Proxy(protocol="http", ip="127.0.0.1",
                               port=up.server_address[1], score=90)])
            import socket as _s
            tmp = _s.socket(); tmp.bind(("127.0.0.1", 0))
            free = tmp.getsockname()[1]; tmp.close()
            stop = serve_socks5(pool, free)
            try:
                out = _socks5_client(free, "api.ipify.org", 80,
                                     b"GET / HTTP/1.0\r\nHost: api.ipify.org\r\n\r\n")
                assert b"198.51.100.7" in out
            finally:
                stop.set()
        finally:
            up.shutdown()
    finally:
        standin.shutdown()


def test_socks5_rejects_udp_associate():
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=18080, score=90)])
    import socket as _s
    tmp = _s.socket(); tmp.bind(("127.0.0.1", 0))
    free = tmp.getsockname()[1]; tmp.close()
    stop = serve_socks5(pool, free)
    try:
        s = socket.create_connection(("127.0.0.1", free), timeout=5)
        s.sendall(b"\x05\x01\x00")
        assert s.recv(2) == b"\x05\x00"
        s.sendall(b"\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00")
        resp = s.recv(10)
        assert resp[1] == 0x07  # command not supported
        s.close()
    finally:
        stop.set()
