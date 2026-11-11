"""Tes v2.1.0: shim kompatibilitas `proxyx` (deprecated, hapus di v3.0.0)."""
import subprocess
import sys

import proxyx
import proxyz


def test_shim_version_matches():
    assert proxyx.__version__ == proxyz.__version__


def test_shim_submodule_delegates():
    from proxyx.gateway import make_handler
    from proxyz.gateway import make_handler as real
    assert make_handler is real


def test_shim_warns_on_import():
    out = subprocess.run([sys.executable, "-W", "always", "-c", "import proxyx"],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0
    assert "proxyz" in out.stderr and "DeprecationWarning" in out.stderr


def test_shim_cli_still_runs():
    out = subprocess.run([sys.executable, "-m", "proxyx", "--version"],
                         capture_output=True, text=True, timeout=30,
                         cwd=".")
    assert out.returncode == 0
    assert "proxyz 2.1.0" in out.stdout
    assert "proxyx" in out.stderr and "proxyz" in out.stderr
