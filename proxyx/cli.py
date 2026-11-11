"""Proxyx — CLI + menu interaktif.

Subcommand (lebih rapi dari 25 flag boolean repo asli):
  python -m proxyx panen --jumlah 20 --negara ID
  python -m proxyx gateway --port 8888
  python -m proxyx warp [--jumlah N]
  python -m proxyx residential [--api-key KEY | --signup]
  python -m proxyx cek <file> [--jumlah N]
  python -m proxyx            (tanpa argumen = menu interaktif)
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .checker import check_pool_sync, enrich_geo
from .exporter import export_all
from .harvester import harvest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def _panen(jumlah: int, negara: str, protokol: str, geo: bool):
    print(f"\n  🌾 Panen proxy (target {jumlah} hidup"
          + (f", negara {negara.upper()}" if negara else "") + ") ...")
    kandidat = harvest(protocols=[protokol] if protokol != "all" else None,
                       country=negara)
    print(f"  📦 Dapat {len(kandidat):,} kandidat mentah")
    hidup = check_pool_sync(kandidat, target=jumlah)
    if geo and hidup:
        print("  🌍 Mengisi data negara (batch) ...")
        enrich_geo(hidup)
    print(f"  ✅ Hidup: {len(hidup)}")
    for p in hidup:
        print(f"    ✓ {p.protocol:6} {p.hostport:22} {str(p.ms or ''):>4} ms "
              f"{p.anonymity:11} skor {p.score} {p.country_code}")
    if hidup:
        paths = export_all(hidup, OUT_DIR)
        print("  💾 Tersimpan:")
        for fmt, path in paths.items():
            print(f"     {fmt:5} {path}")
    else:
        print("  ! Tidak ada yang hidup — coba lagi nanti / ganti jaringan.")
    return hidup


def _cmd_panen(a):
    _panen(a.jumlah, a.negara, a.protokol, a.geo)


def _cmd_cek(a):
    from .checker import check_one, get_host_ip
    import asyncio
    from .models import Proxy
    cands = []
    with open(a.file, encoding="utf-8", errors="ignore") as f:
        for line in f:
            p = Proxy.from_string(line, source="file")
            if p:
                cands.append({"protocol": p.protocol, "ip": p.ip, "port": p.port})
    hidup = check_pool_sync(cands, target=a.jumlah, max_check=len(cands) or 300)
    print(f"  ✅ Hidup: {len(hidup)} dari {len(cands)}")
    for p in hidup:
        print(f"    ✓ {p.protocol:6} {p.hostport:22} {str(p.ms or ''):>4} ms {p.anonymity}")
    if hidup:
        export_all(hidup, OUT_DIR)


def _cmd_gateway(a):
    from .checker import check_pool_sync
    from .gateway import load_pool_from_disk, serve
    from .pool import Pool
    pool = Pool(load_pool_from_disk())
    print(f"  Pool awal: {len(pool)} proxy")
    if len(pool) == 0:
        print("  Pool kosong — panen dulu ...")
        hidup = _panen(10, "", "all", False)
        pool.add(hidup)

    def refill(target: int = 10):
        kandidat = harvest()
        return check_pool_sync(kandidat, target=target)

    serve(pool, port=a.port, healer=not a.no_healer, refill_fn=refill)


def _cmd_warp(a):
    from .warp import generate_and_save
    print("\n  ☁️  Daftar akun WARP via API resmi Cloudflare ...")
    try:
        profiles = generate_and_save(os.path.join(OUT_DIR, "warp"), count=a.jumlah)
    except RuntimeError as e:
        print(f"  ✗ {e}")
        return
    for p in profiles:
        print(f"  ✓ Akun {p['account_id']} — endpoint {p['endpoint']}")
    print(f"  💾 Tersimpan di {os.path.join(OUT_DIR, 'warp')}/ (mode 0600)")
    print("  JANGAN bagikan file warp*.conf — isinya private key kamu.")


def _cmd_residential(a):
    from .residential import (fetch_webshare, guided_signup, load_api_key,
                              load_manual, save_api_key)
    if a.signup:
        pw = guided_signup(open_browser=True)
        print("\n  📝 Daftar manual di https://proxy.webshare.io/register")
        print(f"  Password yang disarankan (simpan baik-baik): {pw}")
        print("  Isi captcha sendiri, lalu ambil API key dari dashboard.")
        return
    key = a.api_key or load_api_key()
    if a.api_key:
        save_api_key(a.api_key)
        print("  ✓ API key disimpan lokal (config/webshare.json, 0600).")
    if not key:
        print("  ✗ Belum ada API key. Jalankan: python -m proxyx residential --signup")
        print("    lalu: python -m proxyx residential --api-key KUNCIMU")
        return
    try:
        proxies = fetch_webshare(key)
    except ValueError:
        print("  ✗ API key ditolak Webshare. Periksa lagi key-nya.")
        return
    except RuntimeError as e:
        print(f"  ✗ {e}")
        return
    manual = load_manual()
    print(f"  ✅ Webshare: {len(proxies)} proxy residential | manual: {len(manual)}")
    for p in proxies[:10]:
        print(f"    • {p.url} [{p.country_code}]")
    if proxies or manual:
        from .exporter import export_all
        export_all(proxies + manual, OUT_DIR)


def _menu():
    print(f"\n  ⚡ PROXYX v{__version__} — panen, cek, gateway, WARP, residential")
    pool_n = 0
    try:
        from .gateway import load_pool_from_disk
        pool_n = len(load_pool_from_disk())
    except Exception:
        pass
    print(f"  Pool saat ini: {pool_n} proxy  (output/proxy_hidup.txt)\n")
    print("  [1] Panen + Cek (langsung dapat proxy hidup)")
    print("  [2] Jalankan Gateway 127.0.0.1:8888")
    print("  [3] Buat WARP WireGuard (.conf)")
    print("  [4] Residential Webshare (API resmi / daftar manual)")
    print("  [5] Tes IP asli vs IP proxy")
    print("  [0] Keluar")
    try:
        pilih = input("\n  Pilih [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        print()
        return
    try:
        if pilih == "1":
            j = int(input("  Mau berapa proxy hidup [20]: ").strip() or "20")
            n = input("  Kode negara (ID/SG/US, kosong = semua): ").strip()
            _panen(j, n, "all", False)
        elif pilih == "2":
            port = int(input("  Port gateway [8888]: ").strip() or "8888")
            _cmd_gateway(argparse.Namespace(port=port, no_healer=False))
        elif pilih == "3":
            _cmd_warp(argparse.Namespace(jumlah=1))
        elif pilih == "4":
            _cmd_residential(argparse.Namespace(api_key="", signup=False))
        elif pilih == "5":
            from .checker import get_host_ip
            import urllib.request
            print(f"\n  IP asli kamu: {get_host_ip()}")
            print("  (bandingkan lewat gateway: curl -x http://127.0.0.1:8888 http://api.ipify.org)")
        elif pilih == "0":
            print("\n  Dadah 👋\n")
            return
        else:
            print("  Pilih 0-5 ya.")
    except KeyboardInterrupt:
        print("\n  Dadah 👋\n")
        return
    except ValueError:
        print("  Angka tidak valid.")
    input("\n  [Enter untuk kembali]")
    _menu()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="proxyx", description="Proxyx — panen proxy, gateway, WARP.")
    p.add_argument("--version", action="version", version=f"proxyx {__version__}")
    sub = p.add_subparsers(dest="cmd")
    sp = sub.add_parser("panen", help="panen + cek proxy hidup")
    sp.add_argument("--jumlah", type=int, default=20)
    sp.add_argument("--negara", default="")
    sp.add_argument("--protokol", default="all", choices=["all", "http", "socks4", "socks5"])
    sp.add_argument("--geo", action="store_true", help="isi negara/kota/ISP (batch)")
    sp.set_defaults(func=_cmd_panen)
    sc = sub.add_parser("cek", help="cek daftar proxy dari file")
    sc.add_argument("file")
    sc.add_argument("--jumlah", type=int, default=20)
    sc.set_defaults(func=_cmd_cek)
    sg = sub.add_parser("gateway", help="jalankan gateway rotating")
    sg.add_argument("--port", type=int, default=8888)
    sg.add_argument("--no-healer", action="store_true")
    sg.set_defaults(func=_cmd_gateway)
    sw = sub.add_parser("warp", help="buat profil WARP WireGuard")
    sw.add_argument("--jumlah", type=int, default=1)
    sw.set_defaults(func=_cmd_warp)
    sr = sub.add_parser("residential", help="proxy residential Webshare")
    sr.add_argument("--api-key", default="")
    sr.add_argument("--signup", action="store_true", help="panduan daftar manual")
    sr.set_defaults(func=_cmd_residential)
    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        _menu()
        return
    args.func(args)


if __name__ == "__main__":
    main()
