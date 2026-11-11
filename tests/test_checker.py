"""Tes checker Proxyx: klasifikasi anonimitas, skor, dan cek HTTP live
melawan proxy dummy di localhost (bukan internet — sandbox memblokir
koneksi TCP langsung ke proxy publik, tapi localhost diizinkan)."""
import threading

import pytest

from proxyx.checker import check_http, classify_anonymity, score_proxy
from proxyx.models import Proxy

HOST = "203.0.113.99"  # TEST-NET-3, tidak akan sama dengan IP egress dummy


def test_classify_transparent_same_ip():
    assert classify_anonymity(HOST, HOST, {}) == "transparent"


def test_classify_transparent_leaked_in_header():
    assert classify_anonymity("1.1.1.1", HOST, {"X-Custom": f"for {HOST}"}) == "transparent"


def test_classify_anonymous_via_header():
    assert classify_anonymity("1.1.1.1", HOST, {"Via": "1.1 proxy"}) == "anonymous"


def test_classify_elite_clean():
    assert classify_anonymity("1.1.1.1", HOST, {"Server": "cloudflare"}) == "elite"


def test_score_elite_fast_beats_transparent():
    assert score_proxy("elite", 120) > score_proxy("transparent", 120)
    assert score_proxy("elite", 120) > score_proxy("elite", 1500)
    assert score_proxy("elite", 100) == 95
    assert 0 <= score_proxy("transparent", 5000) <= 45


# ---- cek HTTP live melawan proxy dummy localhost ----
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.request
import json


class DummyProxy(BaseHTTPRequestHandler):
    """Forward proxy pura-pura: GET http://api.ipify.org/... -> jawab IP palsu.
    Egress palsu beda dari HOST, tanpa header via -> harus terdeteksi elite."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"ip": "198.51.100.7"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def dummy_proxy():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), DummyProxy)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv.server_address[1]
    srv.shutdown()


@pytest.mark.asyncio
async def test_check_http_via_dummy_proxy(dummy_proxy):
    p = Proxy(protocol="http", ip="127.0.0.1", port=dummy_proxy)
    # URL http (bukan https) supaya dummy GET-only cukup; default produksi tetap HTTPS.
    out = await check_http(p, HOST, timeout=5, test_url="http://api.ipify.org?format=json")
    assert out is not None
    assert out.egress_ip == "198.51.100.7"
    assert out.anonymity == "elite"
    assert out.ms is not None and out.ms >= 0
    assert out.score == 95


@pytest.mark.asyncio
async def test_check_http_dead_proxy():
    p = Proxy(protocol="http", ip="127.0.0.1", port=9)  # discard, tidak ada yang listen
    out = await check_http(p, HOST, timeout=3)
    assert out is None
