"""Tes v1.7.0: blacklist + tier kecepatan."""
from proxyx.blacklist import (add_to_blacklist, filter_blacklisted,
                              is_blacklisted, load_blacklist,
                              remove_from_blacklist)
from proxyx.models import Proxy
from proxyx.tiers import filter_tier, tier_of


def test_blacklist_crud(tmp_path, monkeypatch):
    import proxyx.blacklist as bl
    monkeypatch.setattr(bl, "BLACKLIST_FILE", str(tmp_path / "blacklist.txt"))
    assert load_blacklist() == set()
    assert add_to_blacklist("1.2.3.4:8080")
    assert not add_to_blacklist("1.2.3.4:8080")  # duplikat ditolak
    assert add_to_blacklist("5.6.7.8")
    assert load_blacklist() == {"1.2.3.4:8080", "5.6.7.8"}
    assert remove_from_blacklist("5.6.7.8")
    assert not remove_from_blacklist("5.6.7.8")
    assert load_blacklist() == {"1.2.3.4:8080"}


def test_is_blacklisted_ip_and_hostport():
    entries = {"1.2.3.4", "5.6.7.8:1080"}
    assert is_blacklisted(Proxy(protocol="http", ip="1.2.3.4", port=9999), entries)
    assert is_blacklisted(Proxy(protocol="socks5", ip="5.6.7.8", port=1080), entries)
    assert not is_blacklisted(Proxy(protocol="socks5", ip="5.6.7.8", port=1081), entries)
    assert not is_blacklisted(Proxy(protocol="http", ip="9.9.9.9", port=8080), entries)


def test_filter_blacklisted_dicts():
    cands = [{"protocol": "http", "ip": "1.1.1.1", "port": 80},
             {"protocol": "http", "ip": "2.2.2.2", "port": 80}]
    out = filter_blacklisted(cands, {"2.2.2.2"})
    assert [c["ip"] for c in out] == ["1.1.1.1"]


def test_tier_classification():
    assert tier_of(Proxy(protocol="http", ip="1.1.1.1", port=80, ms=120)) == "cepat"
    assert tier_of(Proxy(protocol="http", ip="1.1.1.1", port=80, ms=500)) == "sedang"
    assert tier_of(Proxy(protocol="http", ip="1.1.1.1", port=80, ms=2000)) == "lambat"
    assert tier_of(Proxy(protocol="http", ip="1.1.1.1", port=80)) == "lambat"


def test_filter_tier():
    ps = [Proxy(protocol="http", ip=f"1.1.1.{i}", port=80, ms=ms)
          for i, ms in enumerate([100, 500, 900, None], 1)]
    assert len(filter_tier(ps, "cepat")) == 1
    assert len(filter_tier(ps, "sedang")) == 2
    assert len(filter_tier(ps, "lambat")) == 4
    assert len(filter_tier(ps, "ngawur")) == 4
