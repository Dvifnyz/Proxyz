"""Tes Tahap 6: kesehatan sumber + residential multi-akun."""
import json
import time

from proxyz import harvester, residential


# ------------------------------------------------------------------ health
def test_should_skip_rules():
    now = time.time()
    assert harvester.should_skip("http://x", {"http://x": {"fails": 3, "last_fail": now}}, now)
    assert not harvester.should_skip("http://x", {"http://x": {"fails": 2, "last_fail": now}}, now)
    assert not harvester.should_skip("http://x", {"http://x": {"fails": 5, "last_fail": now - 7200}}, now)
    assert not harvester.should_skip("http://x", {}, now)


def test_update_health_ok_resets_fails():
    h = {}
    harvester.update_health(h, "http://x", False, 0, now=1000.0)
    harvester.update_health(h, "http://x", False, 0, now=1001.0)
    assert h["http://x"]["fails"] == 2
    harvester.update_health(h, "http://x", True, 7, now=1002.0)
    assert h["http://x"]["fails"] == 0 and h["http://x"]["yield"] == 7


def test_build_jobs_skips_dead_source(tmp_path):
    src = tmp_path / "sources.json"
    src.write_text(json.dumps({
        "http": ["https://sehat.example/a.txt", "https://mati.example/b.txt"],
    }))
    health = {"https://mati.example/b.txt": {"fails": 3, "last_fail": time.time()}}
    jobs = harvester.build_jobs(["http"], sources_path=str(src), health=health)
    assert [u for u, _ in jobs] == ["https://sehat.example/a.txt"]


def test_record_health_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(harvester, "HEALTH_FILE", str(tmp_path / "health.json"))
    jobs = [("https://a.example/x.txt", "http"), ("https://b.example/y.txt", "http")]
    harvester._record_health(jobs, [([{"proxy": "1.1.1.1:80"}], True), ([], False)])
    h = harvester.load_health()
    assert h["https://a.example/x.txt"]["fails"] == 0
    assert h["https://a.example/x.txt"]["yield"] == 1
    assert h["https://b.example/y.txt"]["fails"] == 1
    assert harvester.health_report()[0]["url"] == "https://a.example/x.txt"


# ------------------------------------------------------------------ residential multi-akun
def test_load_api_keys_env_plus_file(tmp_path, monkeypatch):
    monkeypatch.setattr(residential, "KEY_FILE", str(tmp_path / "webshare.json"))
    monkeypatch.setenv("WEBSHARE_API_KEY", " key-env , key-file ")
    (tmp_path / "webshare.json").write_text(json.dumps({"api_keys": ["key-file", "key-lain"]}))
    assert residential.load_api_keys() == ["key-env", "key-file", "key-lain"]


def test_load_api_keys_legacy_single(tmp_path, monkeypatch):
    monkeypatch.setattr(residential, "KEY_FILE", str(tmp_path / "webshare.json"))
    monkeypatch.delenv("WEBSHARE_API_KEY", raising=False)
    (tmp_path / "webshare.json").write_text(json.dumps({"api_key": "lama"}))
    assert residential.load_api_keys() == ["lama"]


def test_save_api_key_appends_and_dedups(tmp_path, monkeypatch):
    monkeypatch.setattr(residential, "KEY_FILE", str(tmp_path / "webshare.json"))
    monkeypatch.delenv("WEBSHARE_API_KEY", raising=False)
    residential.save_api_key("k1")
    residential.save_api_key("k2")
    residential.save_api_key("k1")  # duplikat: tidak dobel
    assert residential.load_api_keys() == ["k1", "k2"]


def test_fetch_all_webshare_multi_key(monkeypatch):
    from proxyz.models import Proxy

    def fake_fetch(key):
        if key == "mati":
            raise ValueError("auth")
        return [Proxy(protocol="http", ip="1.1.1.1", port=8080, source="webshare",
                      residential=True)]

    monkeypatch.setattr(residential, "fetch_webshare", fake_fetch)
    out = residential.fetch_all_webshare(["ok", "mati", "ok"])
    assert len(out) == 1  # dedup + akun mati dilewati


def test_legacy_single_key_migrated_on_load(tmp_path, monkeypatch):
    """v2.0.0: file {"api_key": ...} ditulis ulang ke {"api_keys": [...]}."""
    import json as _json
    monkeypatch.setattr(residential, "KEY_FILE", str(tmp_path / "webshare.json"))
    monkeypatch.delenv("WEBSHARE_API_KEY", raising=False)
    (tmp_path / "webshare.json").write_text(_json.dumps({"api_key": "lama"}))
    assert residential.load_api_keys() == ["lama"]
    data = _json.loads((tmp_path / "webshare.json").read_text())
    assert data == {"api_keys": ["lama"]}
    assert residential.load_api_keys() == ["lama"]  # idempotent


def test_validate_api_key(monkeypatch):
    monkeypatch.setattr(residential, "fetch_webshare",
                        lambda k: [object()] if k == "bagus" else (_ for _ in ()).throw(ValueError("auth")))
    ok, info = residential.validate_api_key("bagus")
    assert ok and "1 proxy" in info
    ok, info = residential.validate_api_key("jelek")
    assert not ok and "ditolak" in info
