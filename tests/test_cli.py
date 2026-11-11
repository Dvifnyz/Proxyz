"""Tes v2.1.1: smoke test CLI — semua subcommand punya --help yang jalan,
dan entry point `python -m proxyz` berfungsi. Ini yang sebelumnya
tidak dicover tes sama sekali (cli.py cuma 7% coverage)."""
import subprocess
import sys

import pytest

COMMANDS = [
    "panen", "cek", "gateway", "sync-9router", "test", "update",
    "bench", "install-service", "laporan", "doctor", "auto", "warp",
    "residential", "sources", "blacklist",
]


@pytest.mark.parametrize("cmd", COMMANDS)
def test_subcommand_help(cmd):
    out = subprocess.run([sys.executable, "-m", "proxyz", cmd, "--help"],
                         capture_output=True, text=True, timeout=30,
                         check=False)
    assert out.returncode == 0, out.stderr
    assert "usage:" in out.stdout


def test_main_module_version():
    out = subprocess.run([sys.executable, "-m", "proxyz", "--version"],
                         capture_output=True, text=True, timeout=30,
                         check=False)
    assert out.returncode == 0
    assert out.stdout.strip().startswith("proxyz 2.1.2")


def test_no_proxyx_package():
    """v2.1.2: shim `proxyx` dihapus — cuma ada satu nama, Proxyz.
    `import proxyx` harus gagal, bukan diam-diam jalan."""
    import importlib.util
    assert importlib.util.find_spec("proxyx") is None


def test_compat_shim_shared():
    """aiohttp shim cuma ada sekali (proxyz/compat) dan dipakai bareng
    checker + harvester — bukan duplikat lagi (pylint R0801)."""
    from proxyz import checker, compat, harvester
    assert checker.HAS_AIOHTTP is harvester.HAS_AIOHTTP
    assert checker.aiohttp is harvester.aiohttp is compat.aiohttp
