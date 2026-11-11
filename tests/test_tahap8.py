"""Tes Tahap 8: bench kecepatan, /api/bench, install-service."""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from proxyx import bench, installer
from proxyx.gateway import make_handler
from proxyx.models import Proxy
from proxyx.pool import Pool
from tests.test_gateway import DummyHttpProxy, IpifyStandin, _start_server


def _bench_env(monkeypatch):
    """Dummy HTTP proxy + standin; arahkan SPEED_URL ke standin (http)."""
    standin = _start_server(IpifyStandin)
    DummyHttpProxy.TARGET_PORT = standin.server_address[1]
    up = _start_server(DummyHttpProxy)
    monkeypatch.setattr(bench, "SPEED_URL",
                        f"http://127.0.0.1:{standin.server_address[1]}/")
    return standin, up


def test_bench_pool_ok_and_socks_skipped(monkeypatch):
    standin, up = _bench_env(monkeypatch)
    try:
        proxies = [Proxy(protocol="http", ip="127.0.0.1", port=up.server_address[1]),
                   Proxy(protocol="socks5", ip="127.0.0.1", port=1080)]
        out = bench.bench_pool(proxies)
        assert out[0]["ok"] and out[0]["bytes"] > 0 and out[0]["kbps"] > 0
        assert not out[1]["ok"] and "SOCKS" in out[1]["error"]
    finally:
        up.shutdown(); standin.shutdown()


def test_api_bench_endpoint(monkeypatch):
    standin, up = _bench_env(monkeypatch)
    try:
        pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=up.server_address[1], score=90)])
        gw = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pool))
        threading.Thread(target=gw.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{gw.server_address[1]}/api/bench?jumlah=1",
                    timeout=15) as r:
                data = json.loads(r.read())
            assert len(data) == 1 and data[0]["ok"] and data[0]["kbps"] > 0
        finally:
            gw.shutdown()
    finally:
        up.shutdown(); standin.shutdown()


def test_install_service_files(tmp_path):
    paths = installer.generate(str(tmp_path), "/usr/bin/python3",
                               "/home/rasya/Proxyx", 8888)
    unit = (tmp_path / "proxyx.service").read_text()
    assert "ExecStart=/usr/bin/python3 -m proxyx gateway --port 8888" in unit
    assert "Restart=on-failure" in unit
    xml = (tmp_path / "proxyx-task.xml").read_text()
    assert "LogonTrigger" in xml and "8888" in xml
    bat = (tmp_path / "install-service.bat").read_text()
    assert "schtasks" in bat and "proxyx-task.xml" in bat
    assert set(paths) == {"proxyx.service", "proxyx-task.xml", "install-service.bat"}
