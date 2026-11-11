"""Tes Tahap 9: 9Router sync aman, profil, backup pool."""
import json
import os
import sqlite3

from proxyz import router
from proxyz.config import PROFILES, apply_profile, load_config
from proxyz.exporter import backup_existing, export_all
from proxyz.models import Proxy


def _make_db(path):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE proxyPools (
        id TEXT, isActive INTEGER, testStatus TEXT, data TEXT,
        createdAt TEXT, updatedAt TEXT)""")
    conn.commit()
    conn.close()


def _row(db_path, proxy_url):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT data FROM proxyPools").fetchall()
    conn.close()
    out = []
    for (data,) in rows:
        d = json.loads(data)
        if d.get("proxyUrl") == proxy_url:
            out.append(d)
    return out


def _proxies():
    return [Proxy(protocol="http", ip="1.2.3.4", port=8080, ms=120,
                  country_code="ID"),
            Proxy(protocol="socks5", ip="5.6.7.8", port=1080, ms=300,
                  country_code="SG")]


def test_sync_insert_backup_dedup(tmp_path):
    db = str(tmp_path / "data.sqlite")
    _make_db(db)
    r1 = router.sync_to_9router(_proxies(), db)
    assert r1["ok"] and r1["inserted"] == 2 and r1["skipped"] == 0
    assert os.path.exists(r1["backup"])  # backup dibuat dulu
    assert _row(db, "http://1.2.3.4:8080")[0]["name"].startswith("Proxyz")
    r2 = router.sync_to_9router(_proxies(), db)  # sync ulang: dedup
    assert r2["inserted"] == 0 and r2["skipped"] == 2
    assert len(_row(db, "http://1.2.3.4:8080")) == 1


def test_sync_replace_only_own_rows(tmp_path):
    db = str(tmp_path / "data.sqlite")
    _make_db(db)
    conn = sqlite3.connect(db)
    # Baris "orang lain" + baris unknown — harus selamat dari --ganti.
    for name, url in [("Router Bawaan", "http://9.9.9.9:8080"),
                      ("Lain", "http://8.8.8.8:8080")]:
        conn.execute("INSERT INTO proxyPools VALUES (?,?,?,?,?,?)",
                     ("x", 1, "unknown", json.dumps({"name": name, "proxyUrl": url}),
                      "t", "t"))
    conn.commit(); conn.close()
    router.sync_to_9router(_proxies(), db)
    r = router.sync_to_9router(_proxies(), db, replace=True)
    assert r["deleted"] == 2  # hanya 2 baris Proxyz
    assert r["inserted"] == 2
    conn = sqlite3.connect(db)
    total = conn.execute("SELECT COUNT(*) FROM proxyPools").fetchone()[0]
    conn.close()
    assert total == 4  # 2 baris orang lain + 2 Proxyz baru


def test_sync_missing_db_or_table(tmp_path):
    r = router.sync_to_9router(_proxies(), str(tmp_path / "tidak-ada.sqlite"))
    assert not r["ok"]
    db = str(tmp_path / "kosong.sqlite")
    sqlite3.connect(db).close()
    r = router.sync_to_9router(_proxies(), db)
    assert not r["ok"] and "proxyPools" in r["error"]


def test_profiles_apply():
    cfg = load_config()
    cepat = apply_profile(cfg, "cepat")
    assert cepat["max_latency_ms"] == 350 and cepat["healer_target"] == 10
    scraper = apply_profile(cfg, "scraper")
    assert scraper["session_ttl"] == 60 and scraper["healer_target"] == 30
    hemat = apply_profile(cfg, "hemat")
    assert hemat["session_ttl"] == 1800 and hemat["min_healthy"] == 2
    assert apply_profile(cfg, "ngawur") == cfg
    assert set(PROFILES) == {"scraper", "cepat", "hemat"}


def test_backup_existing_keeps_5(tmp_path):
    import time
    p = tmp_path / "proxy_hidup.txt"
    p.write_text("lama\n")
    for _ in range(7):
        backup_existing(str(p))
        time.sleep(0.01)
    backs = sorted((tmp_path / "backup").iterdir())
    assert len(backs) == 5
    assert p.read_text() == "lama\n"  # file asli tidak berubah


def test_export_all_backs_up(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "proxy_hidup.txt").write_text("versi-1\n")
    export_all(_proxies(), str(out))
    assert (out / "proxy_hidup.txt").read_text() != "versi-1\n"
    assert len(list((out / "backup").iterdir())) == 1  # hanya file yang sudah ada dibackup
