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


def _panen(jumlah: int, negara: str, protokol: str, geo: bool, tier: str = ""):
    print(f"\n  🌾 Panen proxy (target {jumlah} hidup"
          + (f", negara {negara.upper()}" if negara else "") + ") ...")
    kandidat = harvest(protocols=[protokol] if protokol != "all" else None,
                       country=negara)
    print(f"  📦 Dapat {len(kandidat):,} kandidat mentah")
    hidup = check_pool_sync(kandidat, target=jumlah)
    if tier:
        from .tiers import filter_tier
        sebelum = len(hidup)
        hidup = filter_tier(hidup, tier)
        print(f"  🎚️  Tier {tier}: {sebelum} -> {len(hidup)} proxy")
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
    _panen(a.jumlah, a.negara, a.protokol, a.geo, tier=a.tier)


def _cmd_blacklist(a):
    from .blacklist import (add_to_blacklist, load_blacklist,
                            remove_from_blacklist)
    if a.aksi == "list":
        entries = sorted(load_blacklist())
        if not entries:
            print("  Blacklist kosong.")
        else:
            print(f"  Blacklist ({len(entries)}):")
            for e in entries:
                print(f"    • {e}")
        return
    if a.aksi == "add":
        print("  ✅ Ditambahkan." if add_to_blacklist(a.entri)
              else "  Sudah ada di blacklist.")
    elif a.aksi == "remove":
        print("  ✅ Dihapus." if remove_from_blacklist(a.entri)
              else "  Tidak ada di blacklist.")


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
    from .blacklist import filter_blacklisted
    cands = filter_blacklisted(cands)
    hidup = check_pool_sync(cands, target=a.jumlah, max_check=len(cands) or 300)
    print(f"  ✅ Hidup: {len(hidup)} dari {len(cands)}")
    for p in hidup:
        print(f"    ✓ {p.protocol:6} {p.hostport:22} {str(p.ms or ''):>4} ms {p.anonymity}")
    if hidup:
        export_all(hidup, OUT_DIR)


def _cmd_gateway(a):
    from .checker import check_pool_sync
    from .config import load_config
    from .gateway import load_pool_from_disk, serve
    from .pool import Pool
    from .config import apply_profile
    cfg = load_config()
    if getattr(a, "profil", ""):
        cfg = apply_profile(cfg, a.profil)
        print(f"  Profil: {a.profil} "
              f"(target {cfg['healer_target']}, min {cfg['min_healthy']}, "
              f"sesi {cfg['session_ttl']} dtk, maks {cfg['max_latency_ms']} ms)")
    port = a.port if a.port else cfg["gateway_port"]
    token = cfg.get("token", "")
    proxies = load_pool_from_disk()
    if getattr(a, "profil", "") == "cepat":
        before = len(proxies)
        proxies = [p for p in proxies
                   if p.ms is None or p.ms <= cfg["max_latency_ms"]]
        print(f"  Filter cepat: {before} -> {len(proxies)} proxy (<=350 ms)")
    pool = Pool(proxies, session_ttl=cfg["session_ttl"])
    print(f"  Pool awal: {len(pool)} proxy (config: {cfg['healer_interval']} dtk healer, "
          f"min {cfg['min_healthy']})")
    if len(pool) == 0:
        print("  Pool kosong — panen dulu ...")
        hidup = _panen(cfg["healer_target"], "", "all", False)
        pool.add(hidup)

    def refill(target: int = 10):
        kandidat = harvest()
        return check_pool_sync(kandidat, target=target)

    audit_path = os.path.join(OUT_DIR, "gateway-audit.jsonl") if cfg.get("audit_log") else None
    serve(pool, port=port, healer=not a.no_healer, refill_fn=refill, token=token,
          healer_interval=cfg["healer_interval"],
          rate_limit_per_min=cfg.get("rate_limit_per_min", 60),
          audit_path=audit_path,
          socks_port=getattr(a, "socks", 0) or 0)


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
    from .residential import (fetch_all_webshare, fetch_webshare,
                              guided_signup, load_api_keys, load_manual,
                              save_api_key, validate_api_key)
    if a.signup:
        # Semi-otomatis: semua langkah otomatis KECUALI captcha-nya,
        # yang diisi sendiri oleh pengguna sekali saat daftar.
        pw = guided_signup(open_browser=True)
        print("\n  📝 Pendaftaran dibuka di browser:")
        print("  1. Isi email + password di bawah, selesaikan captcha sendiri.")
        print(f"     Password yang disarankan (simpan baik-baik): {pw}")
        print("  2. Setelah masuk dashboard, salin API key-mu.")
        try:
            key = input("  Tempel API key dari dashboard (Enter = lewati): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not key:
            print("  Nanti bisa ditambah dengan: python -m proxyx residential --api-key KUNCIMU")
            return
        ok, info = validate_api_key(key)
        if ok:
            save_api_key(key)
            print(f"  ✓ Key valid ({info}) — disimpan lokal (config/webshare.json, 0600).")
        else:
            print(f"  ✗ Key tidak valid: {info}")
        return
    if a.api_key:
        ok, info = validate_api_key(a.api_key)
        if ok:
            save_api_key(a.api_key)
            print(f"  ✓ API key valid ({info}) — disimpan lokal.")
        else:
            print(f"  ✗ API key tidak valid: {info}")
            return
    keys = load_api_keys()
    if not keys:
        print("  ✗ Belum ada API key. Jalankan: python -m proxyx residential --signup")
        return
    all_proxies = []
    for i, key in enumerate(keys, 1):
        try:
            got = fetch_webshare(key)
            print(f"  ✅ Akun {i}: {len(got)} proxy residential")
            all_proxies += got
        except Exception as e:
            print(f"  ✗ Akun {i}: gagal ({e})")
    manual = load_manual()
    print(f"  Manual: {len(manual)} proxy | Total residential: {len(all_proxies) + len(manual)}")
    for p in (all_proxies + manual)[:10]:
        print(f"    • {p.url} [{p.country_code}]")
    if all_proxies or manual:
        from .exporter import export_all
        export_all(all_proxies + manual, OUT_DIR)


def _cmd_test(a):
    """Leak test: IP asli vs IP lewat gateway yang sedang jalan."""
    from .checker import get_host_ip
    import re
    import urllib.request
    cfg_port = a.port
    direct = get_host_ip()
    gw_ip = ""
    try:
        proxy = f"http://127.0.0.1:{cfg_port}"
        h = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(h)
        req = urllib.request.Request("http://api.ipify.org",
                                     headers={"User-Agent": "Proxyx/1.0"})
        with opener.open(req, timeout=10) as r:
            gw_ip = r.read().decode().strip()
    except Exception as e:
        print(f"  ✗ Tidak bisa menjangkau gateway di 127.0.0.1:{cfg_port} ({e})")
        print("    Jalankan dulu: python -m proxyx gateway")
        return
    print(f"  IP asli kamu : {direct or '(tidak terdeteksi)'}")
    print(f"  IP via gateway: {gw_ip or '(tidak terdeteksi)'}")
    if direct and gw_ip and direct != gw_ip and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", gw_ip):
        print("  ✅ ZERO LEAK — IP aslimu tidak bocor.")
    else:
        print("  ⚠️  Hasil tidak meyakinkan — periksa pool gateway / koneksi.")


def _cmd_bench(a):
    from .bench import bench_pool
    from .gateway import load_pool_from_disk
    proxies = [p for p in load_pool_from_disk() if p.protocol == "http"][:a.jumlah]
    if not proxies:
        print("  ✗ Pool kosong / tidak ada proxy HTTP. Panen dulu: python -m proxyx panen")
        return
    print(f"\n  ⚡ Bench {len(proxies)} proxy HTTP (unduh 1 MB tiap proxy) ...")
    results = bench_pool(proxies, workers=a.workers)
    for i, r in enumerate(results, 1):
        if r["ok"]:
            print(f"  {i:>2}. {r['proxy']:22} {r['kbps']:>8} KB/detik  ({r['seconds']} dtk)")
        else:
            print(f"  {i:>2}. {r['proxy']:22} GAGAL: {r['error']}")
    import json
    path = os.path.join(OUT_DIR, "bench.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Tersimpan: {path}")


def _cmd_doctor(a):
    import sys
    from .doctor import print_doctor, run_doctor
    result = run_doctor(check_gateway=not a.no_gateway)
    print_doctor(result)
    if not result["healthy"]:
        sys.exit(1)


def _cmd_laporan(a):
    from .gateway import load_pool_from_disk
    from .harvester import health_report
    from .report import build_report, load_bench_results, report_markdown
    data = build_report(load_pool_from_disk(), health_report(),
                        load_bench_results())
    md = report_markdown(data)
    path = os.path.join(OUT_DIR, "laporan.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n  📋 Laporan Proxyx — {data['generated_at']}")
    print(f"  Pool: {data['pool_total']} proxy | Tier: {data['by_tier']}")
    print(f"  Sumber mati: {data['dead_sources']} | Bench top: "
          f"{data['bench_top'][0]['proxy'] if data['bench_top'] else '-'}")
    print(f"  💾 Tersimpan: {path}")


def _cmd_auto(a):
    from .config import load_config
    from .scheduler import LOG_PATH, run_scheduler
    cfg = load_config()
    interval = a.interval if a.interval else cfg["schedule_interval_min"]
    target = a.jumlah if a.jumlah else cfg["schedule_target"]
    print(f"\n  🔁 Mode auto: siklus tiap {interval} menit, target {target} hidup.")
    print("  Ctrl+C untuk berhenti.\n")
    try:
        run_scheduler(interval_min=interval, target=target,
                      once=a.sekali, log_path=LOG_PATH)
    except KeyboardInterrupt:
        print("\n  Auto berhenti.")


def _cmd_sync_9router(a):
    from .gateway import load_pool_from_disk
    from .router import find_9router_db, sync_to_9router
    proxies = load_pool_from_disk()
    if not proxies:
        print("  ✗ Pool kosong. Panen dulu: python -m proxyx panen")
        return
    db = a.db or find_9router_db()
    if not db:
        print("  ✗ DB 9Router tidak ditemukan. Beri jalurnya:")
        print("    python -m proxyx sync-9router --db C:/path/ke/data.sqlite")
        print("    (atau set env ROUTER_DB_PATH)")
        return
    if a.ganti and not a.yes:
        try:
            jawab = input("  --ganti akan menghapus baris 'Proxyx' lama di DB. Lanjut? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if jawab != "y":
            print("  Dibatalkan.")
            return
    res = sync_to_9router(proxies, db, replace=a.ganti)
    if not res.get("ok"):
        print(f"  ✗ {res.get('error')}")
        return
    print(f"  ✅ 9Router: {res['inserted']} ditambah, {res['skipped']} sudah ada"
          + (f", {res['deleted']} baris Proxyx lama dihapus" if res['deleted'] else ""))
    print(f"  💾 Backup DB: {res['backup']}")


def _cmd_install_service(a):
    from .config import load_config
    from .installer import generate
    import sys
    cfg = load_config()
    port = a.port if a.port else cfg["gateway_port"]
    paths = generate(OUT_DIR, sys.executable, BASE_DIR, port)
    print("\n  🔧 File service dibuat:")
    for name, path in paths.items():
        print(f"     {name:20} {path}")
    print("\n  Linux (systemd):")
    print(f"    sudo cp {paths['proxyx.service']} /etc/systemd/system/")
    print("    sudo systemctl daemon-reload && sudo systemctl enable --now proxyx")
    print("\n  Windows (klik kanan install-service.bat > Run as administrator).")
    print("  Gateway akan jalan otomatis tiap mesin nyala / login.")


def _cmd_update(a):
    from .updater import check_update, update_via_pip
    info = check_update(__version__)
    if info.get("error"):
        print(f"  ✗ {info['error']}")
        return
    print(f"  Versi sekarang: {info['current']} | terbaru: {info['latest']}")
    if not info["update_available"]:
        print("  ✅ Kamu sudah memakai versi terbaru.")
        return
    print(f"  Rilis: {info.get('url', '')}")
    if info.get("notes"):
        print(f"  Catatan: {info['notes'][:200]}")
    if not a.yes:
        try:
            jawab = input("  Update sekarang? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if jawab != "y":
            print("  Dibatalkan.")
            return
    ok, msg = update_via_pip(info["latest"])
    print(f"  {'✅' if ok else '✗'} {msg}")


def _cmd_sources(a):
    from .harvester import health_report
    rows = health_report()
    if not rows:
        print("  Belum ada riwayat panen. Jalankan `python -m proxyx panen` dulu.")
        return
    print(f"\n  {'SUMBER':50} {'HASIL':>8} {'GAGAL':>6}  STATUS")
    for r in rows:
        status = "ISTIRAHAT" if r.get("fails", 0) >= 3 else "aktif"
        print(f"  {r['url'][:50]:50} {r.get('yield', 0):>8} {r.get('fails', 0):>6}  {status}")
    print("  (sumber yang gagal 3x beruntun diistirahatkan 1 jam)")


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
    print("  [6] Sinkron pool ke 9Router")
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
            from .config import load_config
            _cmd_test(argparse.Namespace(port=load_config()["gateway_port"]))
        elif pilih == "6":
            _cmd_sync_9router(argparse.Namespace(db="", ganti=False, yes=False))
        elif pilih == "0":
            print("\n  Dadah 👋\n")
            return
        else:
            print("  Pilih 0-6 ya.")
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
    sp.add_argument("--tier", default="", choices=["", "cepat", "sedang", "lambat"],
                    help="saring hasil hidup berdasarkan kecepatan")
    sp.add_argument("--geo", action="store_true", help="isi negara/kota/ISP (batch)")
    sp.set_defaults(func=_cmd_panen)
    sb2 = sub.add_parser("blacklist", help="kelola proxy yang tidak boleh dipakai")
    sb2.add_argument("aksi", choices=["add", "remove", "list"])
    sb2.add_argument("entri", nargs="?", default="")
    sb2.set_defaults(func=_cmd_blacklist)
    sc = sub.add_parser("cek", help="cek daftar proxy dari file")
    sc.add_argument("file")
    sc.add_argument("--jumlah", type=int, default=20)
    sc.set_defaults(func=_cmd_cek)
    sg = sub.add_parser("gateway", help="jalankan gateway rotating")
    sg.add_argument("--port", type=int, default=0, help="0 = pakai config/proxyx.json")
    sg.add_argument("--profil", default="", choices=["", "scraper", "cepat", "hemat"])
    sg.add_argument("--socks", type=int, default=0, help="nyalakan juga listener SOCKS5 di port ini")
    sg.add_argument("--no-healer", action="store_true")
    sg.set_defaults(func=_cmd_gateway)
    s9 = sub.add_parser("sync-9router", help="sinkronkan pool ke DB SQLite 9Router (aman)")
    s9.add_argument("--db", default="")
    s9.add_argument("--ganti", action="store_true",
                    help="hapus baris 'Proxyx' lama dulu (hanya milik Proxyx)")
    s9.add_argument("--yes", action="store_true")
    s9.set_defaults(func=_cmd_sync_9router)
    st = sub.add_parser("test", help="leak test: IP asli vs IP via gateway")
    st.add_argument("--port", type=int, default=8888)
    st.set_defaults(func=_cmd_test)
    su = sub.add_parser("update", help="cek & pasang rilis terbaru (aman, via pip)")
    su.add_argument("--yes", action="store_true", help="update tanpa konfirmasi")
    su.set_defaults(func=_cmd_update)
    sb = sub.add_parser("bench", help="uji kecepatan unduh tiap proxy HTTP di pool")
    sb.add_argument("--jumlah", type=int, default=10)
    sb.add_argument("--workers", type=int, default=10)
    sb.set_defaults(func=_cmd_bench)
    si = sub.add_parser("install-service", help="buat file service (systemd + Windows Task)")
    si.add_argument("--port", type=int, default=0, help="0 = pakai config/proxyx.json")
    si.set_defaults(func=_cmd_install_service)
    sl = sub.add_parser("laporan", help="ringkasan kesehatan pool (output/laporan.md)")
    sl.set_defaults(func=_cmd_laporan)
    sd = sub.add_parser("doctor", help="diagnosa mandiri: config, sumber, pool, gateway")
    sd.add_argument("--no-gateway", action="store_true", help="lewati cek gateway")
    sd.set_defaults(func=_cmd_doctor)
    sa = sub.add_parser("auto", help="panen + cek + ekspor berkala, tanpa henti")
    sa.add_argument("--interval", type=float, default=0, help="menit antar siklus (0 = config)")
    sa.add_argument("--jumlah", type=int, default=0, help="target hidup per siklus (0 = config)")
    sa.add_argument("--sekali", action="store_true", help="satu siklus saja (untuk cron)")
    sa.set_defaults(func=_cmd_auto)
    sw = sub.add_parser("warp", help="buat profil WARP WireGuard")
    sw.add_argument("--jumlah", type=int, default=1)
    sw.set_defaults(func=_cmd_warp)
    sr = sub.add_parser("residential", help="proxy residential Webshare")
    sr.add_argument("--api-key", default="")
    sr.add_argument("--signup", action="store_true", help="daftar semi-otomatis + simpan key")
    sr.set_defaults(func=_cmd_residential)
    ss = sub.add_parser("sources", help="lihat kesehatan sumber panen")
    ss.set_defaults(func=_cmd_sources)
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
