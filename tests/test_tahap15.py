"""Tes v1.9.0: doctor diagnostics."""
import json
import os

from proxyx.doctor import print_doctor, run_doctor


def test_doctor_real_project_healthy():
    r = run_doctor(check_gateway=False)
    names = {c["name"] for c in r["checks"]}
    assert {"Python", "Config", "Sumber panen", "Pool", "Gateway"} - names == {"Gateway"}
    assert r["healthy"]  # tanpa gateway: tidak ada error di proyek nyata
    assert all("ok" in c and "detail" in c for c in r["checks"])


def test_doctor_missing_project_reports_errors(tmp_path):
    r = run_doctor(base_dir=str(tmp_path), check_gateway=False)
    by_name = {c["name"]: c for c in r["checks"]}
    assert by_name["Sumber panen"]["ok"] is False
    assert by_name["Pool"]["ok"] is None  # peringatan, bukan error
    assert not r["healthy"]


def test_doctor_gateway_check(tmp_path):
    r = run_doctor(base_dir=str(tmp_path), gateway_port=59999, check_gateway=True)
    by_name = {c["name"]: c for c in r["checks"]}
    assert by_name["Gateway"]["ok"] is None  # tidak jalan = peringatan


def test_print_doctor_does_not_crash(capsys):
    r = run_doctor(check_gateway=False)
    print_doctor(r)
    out = capsys.readouterr().out
    assert "Proxyx Doctor" in out and ("Sehat" in out or "error" in out)
