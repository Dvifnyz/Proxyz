"""Tes WARP: bangun conf/sing-box dari respons API palsu (mock)."""
import json
import os
import stat

import pytest

from proxyx import warp


def _fake_response(monkeypatch):
    payload = {
        "id": "test-id-123", "token": "test-token",
        "config": {
            "peers": [{"public_key": "PEERKEY=",
                       "endpoint": {"host": "162.159.193.10:2408"}}],
            "interface": {"addresses": {"v4": "172.16.0.2/32",
                                        "v6": "2606:4700:110::2/128"}},
        },
    }

    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(payload).encode()

    monkeypatch.setattr(warp.urllib.request, "urlopen", lambda *a, **k: Resp())
    monkeypatch.setattr(warp, "generate_keypair",
                        lambda: ("PRIVKEY=", "PUBKEY="))


def test_register_account_parses_response(monkeypatch):
    _fake_response(monkeypatch)
    p = warp.register_account()
    assert p["account_id"] == "test-id-123"
    assert p["endpoint"] == "162.159.193.10:2408"
    assert p["v4"] == "172.16.0.2/32"
    assert "PrivateKey = PRIVKEY=" in warp.build_wireguard_conf(p)
    assert "Endpoint = 162.159.193.10:2408" in warp.build_wireguard_conf(p)
    sb = warp.build_singbox_config(p)
    assert sb["outbounds"][0]["server_port"] == 2408
    assert sb["outbounds"][0]["private_key"] == "PRIVKEY="


def test_register_account_incomplete_response(monkeypatch):
    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"id": "x", "config": {}}).encode()
    monkeypatch.setattr(warp.urllib.request, "urlopen", lambda *a, **k: Resp())
    monkeypatch.setattr(warp, "generate_keypair",
                        lambda: ("PRIVKEY=", "PUBKEY="))
    with pytest.raises(RuntimeError, match="tidak lengkap"):
        warp.register_account()


def test_generate_and_save_private_files(monkeypatch, tmp_path):
    _fake_response(monkeypatch)
    profiles = warp.generate_and_save(str(tmp_path), count=1)
    assert len(profiles) == 1
    conf = tmp_path / "warp.conf"
    assert conf.exists()
    mode = stat.S_IMODE(os.stat(conf).st_mode)
    assert mode == 0o600  # private key tidak boleh terbaca orang lain
    assert "PRIVKEY=" in conf.read_text()
