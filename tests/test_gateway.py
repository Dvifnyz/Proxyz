"""Tes pool + gateway Proxyz (live, localhost saja)."""
import json
import socket
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from proxyz.gateway import connect_via_proxy, make_handler
from proxyz.models import Proxy
from proxyz.pool import Pool


# ------------------------------------------------------------------ pool
def test_pool_round_robin_and_residential_first():
    a = Proxy(protocol="http", ip="1.1.1.1", port=80, score=90)
    b = Proxy(protocol="http", ip="2.2.2.2", port=80, score=50)
    c = Proxy(protocol="http", ip="3.3.3.3", port=80, score=10, residential=True)
    pool = Pool([a, b, c])
    # residential (skor 10) tetap di depan karena residential dulu
    assert pool.next().ip == "3.3.3.3"
    assert pool.next().ip == "1.1.1.1"
    assert pool.next().ip == "2.2.2.2"
    assert pool.next().ip == "3.3.3.3"


def test_pool_sticky_session():
    pool = Pool([Proxy(protocol="http", ip="1.1.1.1", port=80, score=90),
                 Proxy(protocol="http", ip="2.2.2.2", port=80, score=80)])
    first = pool.next(session_id="s1")
    assert pool.next(session_id="s1").ip == first.ip
    assert pool.next(session_id="s1").ip == first.ip


def test_pool_evict_after_3_fails():
    p = Proxy(protocol="http", ip="9.9.9.9", port=80, score=90)
    pool = Pool([p, Proxy(protocol="http", ip="1.1.1.1", port=80, score=80)])
    pool.mark_failed(p)
    pool.mark_failed(p)
    assert len(pool) == 2
    pool.mark_failed(p)
    assert len(pool) == 1
    assert pool.stats()["evicted"] == 1


def test_pool_country_filter():
    pool = Pool([Proxy(protocol="http", ip="1.1.1.1", port=80, score=90, country_code="US"),
                 Proxy(protocol="http", ip="2.2.2.2", port=80, score=80, country_code="ID")])
    assert pool.next(country="ID").ip == "2.2.2.2"
    assert pool.next(country="XX").ip in ("1.1.1.1", "2.2.2.2")  # fallback: semua


# ------------------------------------------------------------------ server dummy
class IpifyStandin(BaseHTTPRequestHandler):
    """Berperan sebagai api.ipify.org: jawab IP tetap."""
    IP = "198.51.100.7"

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"ip": self.IP}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DummyHttpProxy(BaseHTTPRequestHandler):
    """Forward proxy HTTP pura-pura: teruskan GET ke IpifyStandin lokal."""
    TARGET_PORT = 0

    def log_message(self, *a):
        pass

    def do_GET(self):
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{self.TARGET_PORT}/", timeout=5) as r:
                body = r.read()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(502, str(e))

    def do_CONNECT(self):
        # Terowongan ke IpifyStandin lokal (abaikan host yang diminta).
        try:
            sock = socket.create_connection(("127.0.0.1", self.TARGET_PORT), timeout=5)
        except Exception:
            self.send_error(502, "target mati")
            return
        self.send_response(200, "Connection Established")
        self.end_headers()

        def pump(src, dst):
            try:
                while True:
                    d = src.recv(8192)
                    if not d:
                        break
                    dst.sendall(d)
            except Exception:
                pass
            finally:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except Exception:
                    pass
        t1 = threading.Thread(target=pump, args=(self.connection, sock), daemon=True)
        t2 = threading.Thread(target=pump, args=(sock, self.connection), daemon=True)
        t1.start(); t2.start()
        t1.join(); t2.join()


class Socks5Stub:
    """Server SOCKS5 tanpa auth: CONNECT apa pun -> IpifyStandin lokal."""

    def __init__(self, target_port):
        self.target_port = target_port
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except Exception:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        try:
            conn.recv(2)  # VER, NMETHODS
            n = conn.recv(1)[0]
            conn.recv(n)
            conn.sendall(b"\x05\x00")
            head = conn.recv(4)
            atyp = head[3]
            if atyp == 1:
                conn.recv(4 + 2)
            elif atyp == 3:
                ln = conn.recv(1)[0]
                conn.recv(ln + 2)
            else:
                conn.recv(16 + 2)
            conn.sendall(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00")
            target = socket.create_connection(("127.0.0.1", self.target_port), timeout=5)
            self._relay(conn, target)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @staticmethod
    def _relay(a, b):
        def pump(src, dst):
            try:
                while True:
                    d = src.recv(8192)
                    if not d:
                        break
                    dst.sendall(d)
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


def _start_server(handler_cls):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture(scope="module")
def standin():
    srv = _start_server(IpifyStandin)
    yield srv.server_address[1]
    srv.shutdown()


@pytest.fixture(scope="module")
def http_upstream(standin):
    DummyHttpProxy.TARGET_PORT = standin
    srv = _start_server(DummyHttpProxy)
    yield srv.server_address[1]
    srv.shutdown()


@pytest.fixture(scope="module")
def socks_upstream(standin):
    yield Socks5Stub(standin).port


def _gateway_server(pool, token=""):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pool, token=token))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _get_via_gateway(gw_port, url, headers=None):
    handler = urllib.request.ProxyHandler(
        {"http": f"http://127.0.0.1:{gw_port}", "https": f"http://127.0.0.1:{gw_port}"})
    opener = urllib.request.build_opener(handler)
    req = urllib.request.Request(url, headers=headers or {})
    with opener.open(req, timeout=10) as r:
        return r.status, r.read().decode()


def test_gateway_forward_http(http_upstream):
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=http_upstream, score=90)])
    gw = _gateway_server(pool)
    try:
        status, body = _get_via_gateway(gw.server_address[1], "http://api.ipify.org/")
        assert status == 200 and "198.51.100.7" in body
        assert pool.stats()["success_requests"] >= 1
    finally:
        gw.shutdown()


def test_gateway_api_status_and_random(http_upstream):
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=http_upstream, score=90)])
    gw = _gateway_server(pool)
    try:
        port = gw.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as r:
            data = json.loads(r.read())
        assert data["pool"] == 1 and data["http"] == 1
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/random", timeout=5) as r:
            one = json.loads(r.read())
        assert one["proxy"] == f"127.0.0.1:{http_upstream}"
    finally:
        gw.shutdown()


def test_gateway_sticky_session(http_upstream):
    # Dua upstream dummy yang menjawab IP berbeda -> sesi sama harus konsisten.
    class IpA(IpifyStandin):
        IP = "198.51.100.11"
    class IpB(IpifyStandin):
        IP = "198.51.100.22"
    sa = _start_server(IpA)
    sb = _start_server(IpB)

    class ProxyA(DummyHttpProxy):
        TARGET_PORT = sa.server_address[1]
    class ProxyB(DummyHttpProxy):
        TARGET_PORT = sb.server_address[1]
    pa = _start_server(ProxyA)
    pb = _start_server(ProxyB)
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=pa.server_address[1], score=90),
                 Proxy(protocol="http", ip="127.0.0.1", port=pb.server_address[1], score=80)])
    gw = _gateway_server(pool)
    try:
        port = gw.server_address[1]
        h = {"X-Session-ID": "bot-1"}
        _, b1 = _get_via_gateway(port, "http://api.ipify.org/", h)
        _, b2 = _get_via_gateway(port, "http://api.ipify.org/", h)
        assert b1 == b2  # sesi sama -> IP sama
    finally:
        gw.shutdown(); sa.shutdown(); sb.shutdown(); pa.shutdown(); pb.shutdown()


class GetOnlyProxy(BaseHTTPRequestHandler):
    """Proxy HTTP sederhana TANPA CONNECT — hanya GET absolute-URI.
    Regresi: forward HTTP polos tidak boleh memakai CONNECT."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"ip": "198.51.100.7"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_gateway_forward_http_get_only_proxy():
    srv = _start_server(GetOnlyProxy)
    try:
        pool = Pool([Proxy(protocol="http", ip="127.0.0.1",
                           port=srv.server_address[1], score=90)])
        gw = _gateway_server(pool)
        try:
            status, body = _get_via_gateway(gw.server_address[1], "http://api.ipify.org/")
            assert status == 200 and "198.51.100.7" in body
        finally:
            gw.shutdown()
    finally:
        srv.shutdown()


def test_gateway_socks5_upstream(socks_upstream):
    pool = Pool([Proxy(protocol="socks5", ip="127.0.0.1", port=socks_upstream, score=90)])
    gw = _gateway_server(pool)
    try:
        status, body = _get_via_gateway(gw.server_address[1], "http://api.ipify.org/")
        assert status == 200 and "198.51.100.7" in body
    finally:
        gw.shutdown()


def test_connect_via_socks5_direct(socks_upstream, standin):
    up = Proxy(protocol="socks5", ip="127.0.0.1", port=socks_upstream)
    sock = connect_via_proxy(up, "api.ipify.org", 80, timeout=5)
    try:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n")
        raw = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            raw += chunk
        assert b"198.51.100.7" in raw
    finally:
        sock.close()


def test_gateway_token_enforced(http_upstream):
    pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=http_upstream, score=90)])
    gw = _gateway_server(pool, token="rahasia")
    try:
        port = gw.server_address[1]
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5)
        assert ei.value.code == 401
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/status",
                                     headers={"Authorization": "Bearer rahasia"})
        with urllib.request.urlopen(req, timeout=5) as r:
            assert json.loads(r.read())["pool"] == 1
    finally:
        gw.shutdown()
