"""Tes exporter: semua format + penulisan atomik (tanpa file .tmp tersisa)."""
import json
import os

from proxyz.exporter import export_all, export_clash
from proxyz.models import Proxy


def sample():
    return [
        Proxy(protocol="http", ip="1.1.1.1", port=8080, ms=120,
              anonymity="elite", score=95, country_code="US"),
        Proxy(protocol="socks5", ip="2.2.2.2", port=1080, ms=300,
              anonymity="anonymous", score=78, country_code="ID"),
        Proxy(protocol="socks4", ip="3.3.3.3", port=1080, score=0),
    ]


def test_export_all(tmp_path):
    out = export_all(sample(), str(tmp_path))
    assert set(out) == {"txt", "json", "csv", "clash"}
    assert not list(tmp_path.glob("*.tmp"))  # atomik: tidak ada sisa .tmp
    txt = (tmp_path / "proxy_hidup.txt").read_text()
    assert "http://1.1.1.1:8080" in txt and "socks5://2.2.2.2:1080" in txt
    data = json.loads((tmp_path / "proxy_hidup.json").read_text())
    assert len(data) == 3 and data[0]["score"] == 95
    csv = (tmp_path / "proxy_hidup.csv").read_text()
    assert csv.startswith("protocol,ip,port,ms,anonymity,score,")
    assert "elite" in csv


def test_export_clash_skips_socks4(tmp_path):
    path = export_clash(sample(), str(tmp_path / "c.yaml"))
    text = open(path).read()
    assert "type: http" in text and "type: socks5" in text
    assert "3.3.3.3" not in text  # SOCKS4 tidak didukung Clash
    assert "name: PROXYZ" in text and "url-test" in text
