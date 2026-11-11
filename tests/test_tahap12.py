"""Tes v1.6.0: scheduler otomatis."""
from proxyx.scheduler import run_cycle, run_scheduler


def _fake_harvest():
    return [{"protocol": "http", "ip": "1.1.1.1", "port": 8080}]


def _fake_check(cands, target=20, **kw):
    return cands[:target]


def test_run_cycle_counts_and_exports(tmp_path):
    exported = {}
    def fake_export(proxies, out_dir):
        exported["n"] = len(proxies)
        return {"txt": "x.txt"}
    s = run_cycle(harvest_fn=_fake_harvest, check_fn=_fake_check,
                  export_fn=fake_export, target=1,
                  out_dir=str(tmp_path), log_path=None)
    assert s["raw"] == 1 and s["alive"] == 1 and exported["n"] == 1
    assert s["exported"] == ["txt"]


def test_run_cycle_empty_pool_no_export(tmp_path):
    called = []
    def fake_export(proxies, out_dir):
        called.append(1)
        return {}
    s = run_cycle(harvest_fn=lambda: [], check_fn=_fake_check,
                  export_fn=fake_export, target=5,
                  out_dir=str(tmp_path), log_path=None)
    assert s["alive"] == 0 and called == []


def test_run_scheduler_once_returns_summary(tmp_path):
    s = run_scheduler(interval_min=60, target=1, once=True,
                      out_dir=str(tmp_path), log_path=None,
                      harvest_fn=_fake_harvest, check_fn=_fake_check,
                      export_fn=lambda p, d: {"txt": "x"})
    assert s["alive"] == 1
