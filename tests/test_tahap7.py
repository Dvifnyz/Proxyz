"""Tes Tahap 7: config yang dibaca, leak test, Clash live, updater aman."""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from proxyx import config, updater
from proxyx.exporter import clash_yaml
from proxyx.gateway import make_handler
from proxyx.models import Proxy
from proxyx.pool import Pool
from tests.test_gateway import DummyHttpProxy, IpifyStandin, _start_server


# ------------------------------------------------------------------ config
def test_config_defaults_and_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GATEWAY_PORT", raising=False)
    monkeypatch.delenv("PROXYX_TOKEN", raising=False)
    cfg = config.load_config(str(tmp_path / "tidak-ada.json"))
    assert cfg["gateway_port"] == 8888 and cfg["healer_interval"] == 90
    f = tmp_path / "proxyx.json"
    f.write_text(json.dumps({"gateway_port": 9999, "tidak_dikenal": 1}))
    cfg = config.load_config(str(f))
    assert cfg["gateway_port"] == 9999 and "tidak_dikenal" not in cfg
    monkeypatch.setenv("GATEWAY_PORT", "7777")
    cfg = config.load_config(str(f))
    assert cfg["gateway_port"] == 7777  # env menang atas file


# ------------------------------------------------------------------ Clash live
def test_clash_yaml_string():
    out = clash_yaml([Proxy(protocol="http", ip="1.2.3.4", port=8080),
                      Proxy(protocol="socks4", ip="5.6.7.8", port=1080)])
    assert "1.2.3.4" in out and "5.6.7.8" not in out  # socks4 dilewati
    assert "proxy-groups:" in out and "PROXYX" in out


# ------------------------------------------------------------------ updater
class _FakeResp:
    def __init__(self, payload): self.payload = payload
    def read(self): return json.dumps(self.payload).encode()
    def __enter__(self): return self
    def __exit__(self, *a): pass


def test_check_update_newer(monkeypatch):
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda req, timeout=10: _FakeResp({"tag_name": "v9.9.9"}))
    info = updater.check_update("1.1.0")
    assert info["update_available"] and info["latest"] == "v9.9.9"


def test_check_update_current_and_error(monkeypatch):
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda req, timeout=10: _FakeResp({"tag_name": "v1.1.0"}))
    assert not updater.check_update("1.1.0")["update_available"]
    def boom(req, timeout=10): raise RuntimeError("offline")
    monkeypatch.setattr(updater.urllib.request, "urlopen", boom)
    assert "error" in updater.check_update("1.1.0")


def test_update_via_pip_uses_pip_no_shell(monkeypatch):
    seen = {}
    class P:
        returncode = 0; stderr = ""; stdout = "ok"
    def fake_run(cmd, **kw):
        seen["cmd"] = cmd; seen["kw"] = kw
        return P()
    monkeypatch.setattr(updater.subprocess, "run", fake_run)
    ok, msg = updater.update_via_pip("v1.2.0")
    assert ok and "pip" in seen["cmd"] and seen["kw"].get("shell") is not True
    assert "git+" in " ".join(seen["cmd"])


# ------------------------------------------------------------------ leak test + clash endpoint
def test_gateway_leak_test_and_clash():
    standin = _start_server(IpifyStandin)
    try:
        DummyHttpProxy.TARGET_PORT = standin.server_address[1]
        up = _start_server(DummyHttpProxy)
        try:
            pool = Pool([Proxy(protocol="http", ip="127.0.0.1", port=up.server_address[1], score=90)])
            gw = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pool))
            threading.Thread(target=gw.serve_forever, daemon=True).start()
            try:
                port = gw.server_address[1]
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/leak-test", timeout=15) as r:
                    data = json.loads(r.read())
                assert data["gateway_ip"] == "198.51.100.7"
                assert data["direct_ip"]  # IP egress sandbox
                assert data["zero_leak"] is True
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/clash.yaml", timeout=5) as r:
                    body = r.read().decode()
                assert "127.0.0.1" in body and "PROXYX" in body
            finally:
                gw.shutdown()
        finally:
            up.shutdown()
    finally:
        standin.shutdown()
