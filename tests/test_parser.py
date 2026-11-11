"""Tes parser Proxyz: regex sumber + Proxy.from_string."""
from proxyz.models import Proxy
from proxyz.sources import parse_proxies_from_text


def test_parse_plain_list():
    text = "192.168.1.1:8080\n10.0.0.1:3128\nsocks5://1.2.3.4:1080\n"
    out = parse_proxies_from_text(text, "http")
    assert [p["proxy"] for p in out] == ["192.168.1.1:8080", "10.0.0.1:3128", "1.2.3.4:1080"]


def test_parse_rejects_invalid():
    text = "invalid_ip:9999\n256.0.0.1:80\n999.999.999.999:8080\n1.2.3.4:70000\n"
    assert parse_proxies_from_text(text, "http") == []


def test_parse_dedup_is_harvester_job():
    # dedup dilakukan harvester, parser cukup mengembalikan semua match
    text = "1.1.1.1:80\n1.1.1.1:80\n"
    assert len(parse_proxies_from_text(text, "http")) == 2


def test_proxy_from_string_plain():
    p = Proxy.from_string("1.2.3.4:8080")
    assert p and p.protocol == "http" and p.ip == "1.2.3.4" and p.port == 8080
    assert p.url == "http://1.2.3.4:8080"


def test_proxy_from_string_auth():
    p = Proxy.from_string("socks5://user:p@ss@5.6.7.8:1080")
    assert p and p.protocol == "socks5" and p.username == "user"
    assert p.password == "p@ss" and p.url == "socks5://user:p@ss@5.6.7.8:1080"


def test_proxy_from_string_invalid():
    assert Proxy.from_string("bukan-proxy") is None
    assert Proxy.from_string("# komentar") is None
    assert Proxy.from_string("") is None
    assert Proxy.from_string("1.2.3.4:99999") is None
