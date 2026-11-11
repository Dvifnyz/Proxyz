"""Tes modul residential: import manual + Webshare API (mock)."""
import io
import json
import urllib.error

import pytest

from proxyz import residential


def test_load_manual_auth_and_plain(tmp_path):
    f = tmp_path / "proxy_manual.txt"
    f.write_text("# contoh\nhttp://user1:pass1@1.2.3.4:8080\n5.6.7.8:1080\nbukan-proxy\n")
    out = residential.load_manual(str(f))
    assert len(out) == 2
    assert out[0].residential is True  # ber-auth -> privat
    assert out[0].url == "http://user1:pass1@1.2.3.4:8080"
    assert out[1].protocol == "http" and out[1].residential is False


def test_load_manual_missing_file(tmp_path):
    assert residential.load_manual(str(tmp_path / "tidak-ada.txt")) == []


def test_fetch_webshare_ok(monkeypatch):
    payload = {"results": [
        {"proxy_address": "1.2.3.4", "port": 8080, "username": "u1",
         "password": "p1", "country_code": "US"},
        {"proxy_address": "5.6.7.8", "port": 0, "username": "u2",
         "password": "p2", "country_code": "ID"},  # port 0 -> dilewati
    ]}

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(payload).encode()

    monkeypatch.setattr(residential.urllib.request, "urlopen", lambda *a, **k: Resp())
    out = residential.fetch_webshare("kunci-palsu")
    assert len(out) == 1
    assert out[0].residential is True and out[0].source == "webshare"
    assert out[0].url == "http://u1:p1@1.2.3.4:8080"
    assert out[0].country_code == "US"


def test_fetch_webshare_bad_key(monkeypatch):
    def boom(*a, **k):
        raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, io.BytesIO(b""))
    monkeypatch.setattr(residential.urllib.request, "urlopen", boom)
    with pytest.raises(ValueError, match="auth"):
        residential.fetch_webshare("kunci-salah")


def test_guided_signup_password_shape(monkeypatch):
    monkeypatch.setattr(residential.webbrowser, "open", lambda *a, **k: True)
    pw = residential.guided_signup(open_browser=True)
    assert len(pw) == 16 and any(c.isdigit() for c in pw)
