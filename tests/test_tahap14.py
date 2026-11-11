"""Tes v1.8.0: laporan pool + /api/report."""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from proxyx.gateway import make_handler
from proxyx.models import Proxy
from proxyx.pool import Pool
from proxyx.report import build_report, report_markdown


def _pool():
    return [Proxy(protocol="http", ip="1.1.1.1", port=8080, ms=120,
                  country_code="ID"),
            Proxy(protocol="http", ip="2.2.2.2", port=8080, ms=500,
                  country_code="SG"),
            Proxy(protocol="socks5", ip="3.3.3.3", port=1080, ms=2000,
                  country_code="US")]


def test_build_report_aggregates():
    health = [{"url": "https://a.example/x", "yield": 100, "fails": 0},
              {"url": "https://b.example/y", "yield": 5, "fails": 4}]
    bench = [{"proxy": "1.1.1.1:8080", "ok": True, "kbps": 500},
             {"proxy": "2.2.2.2:8080", "ok": False, "error": "timeout"}]
    data = build_report(_pool(), health, bench, {"total_requests": 10})
    assert data["pool_total"] == 3
    assert data["by_protocol"] == {"http": 2, "socks5": 1}
    assert data["by_country"]["ID"] == 1
    assert data["by_tier"] == {"cepat": 1, "sedang": 1, "lambat": 1}
    assert data["dead_sources"] == 1
    assert data["top_sources"][0]["yield"] == 100
    assert data["bench_top"][0]["proxy"] == "1.1.1.1:8080"
    md = report_markdown(data)
    assert "# Laporan Proxyx" in md and "1.1.1.1:8080" in md


def test_build_report_empty():
    data = build_report([], [], [])
    assert data["pool_total"] == 0 and data["bench_top"] == []
    assert "(belum ada riwayat panen)" in report_markdown(data)


def test_api_report_endpoint():
    pool = Pool(_pool())
    gw = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pool))
    threading.Thread(target=gw.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{gw.server_address[1]}/api/report",
                timeout=5) as r:
            data = json.loads(r.read())
        assert data["pool_total"] == 3
        assert data["by_tier"]["cepat"] == 1
    finally:
        gw.shutdown()
