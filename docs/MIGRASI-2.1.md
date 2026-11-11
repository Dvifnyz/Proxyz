# Pindah ke Proxyz v2.1.0

Di v2.1.0 nama tool diganti dari **Proxyx** jadi **Proxyz**,
biar sama kayak nama repo. Kebanyakan pengguna nggak perlu
ngapa-ngapain.

## Yang berubah

| Lama (≤ v2.0.0) | Baru (v2.1.0) |
|---|---|
| `python -m proxyx ...` | `python -m proxyz ...` |
| perintah `proxyx` | perintah `proxyz` |
| `import proxyx...` / `from proxyx... import ...` | `import proxyz...` |
| `pip install proxyx` | `pip install proxyz` |
| `config/proxyx.json` | `config/proxyz.json` |
| env `PROXYX_TOKEN` | env `PROXYZ_TOKEN` |
| header `X-Proxyx-Token` | header `X-Proxyz-Token` |
| baris 9Router `Proxyx [...]` | baris 9Router `Proxyz [...]` |

## Yang lama masih jalan

Sampai **v3.0.0**, yang lama tetap berfungsi:

- Perintah `proxyx ...` masih jalan (ngasih peringatan sekali).
- `python -m proxyx ...` masih jalan (peringatan ke stderr).
- `import proxyx` / `from proxyx.gateway import ...` masih jalan
  (peringatan `DeprecationWarning`).
- Env `PROXYX_TOKEN` dan header `X-Proxyx-Token` tetap dibaca
  (kalah kalau `PROXYX_TOKEN` juga diisi).
- `proxyz sync-9router --ganti` bersihin baris nama lama
  `Proxyx` juga.

Setelah v3.0.0, semua yang lama dihapus.

## Kalau mau pindah sekarang

```bash
python -m proxyz update          # tarik v2.1.0
mv config/proxyx.json config/proxyz.json   # kalau kamu punya file config lama
# ganti PROXYX_TOKEN -> PROXYZ_TOKEN di env / service kamu
# ganti `proxyx` -> `proxyz` di script / systemd unit / cron kamu
python -m proxyz doctor          # pastiin semuanya sehat
```

Yang nggak berubah: perilaku semua perintah, format file
`output/`, sama API Python (selain nama paket). Nggak ada data
yang hilang: pool, blacklist, kesehatan sumber, sama key Webshare
nggak disentuh rename ini.
