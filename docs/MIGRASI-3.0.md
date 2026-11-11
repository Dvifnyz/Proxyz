# Migrasi ke Proxyz v3.0.0

Di v3.0.0 nama tool diganti dari **Proxyx** menjadi **Proxyz**
(sesuai nama repo `Dvifnyz/Proxyz`). Ini panduan migrasinya —
kebanyakan pengguna tidak perlu melakukan apa pun.

## Yang berubah

| Lama (v2.x) | Baru (v3.0.0) |
|---|---|
| `python -m proxyx ...` | `python -m proxyz ...` |
| perintah `proxyx` | perintah `proxyz` |
| `import proxyx...` / `from proxyx... import ...` | `import proxyz...` |
| `pip install proxyx` | `pip install proxyz` |
| `config/proxyx.json` | `config/proxyz.json` |
| env `PROXYX_TOKEN` | env `PROXYZ_TOKEN` |
| header `X-Proxyx-Token` | header `X-Proxyz-Token` |
| baris 9Router `Proxyx [...]` | baris 9Router `Proxyz [...]` |

## Yang tetap jalan (kompatibilitas)

Sampai **v4.0.0**, yang lama tetap berfungsi:

- Perintah `proxyx ...` masih jalan (menampilkan peringatan sekali).
- `python -m proxyx ...` masih jalan (peringatan ke stderr).
- `import proxyx` / `from proxyx.gateway import ...` masih jalan
  (peringatan `DeprecationWarning`).
- Env `PROXYX_TOKEN` dan header `X-Proxyx-Token` tetap dibaca
  (kalah bila `PROXYZ_TOKEN` juga diisi).
- `proxyz sync-9router --ganti` membersihkan baris nama lama
  `Proxyx` juga.

Setelah v4.0.0, semua yang lama dihapus.

## Langkah migrasi (disarankan)

```bash
python -m proxyz update          # tarik v3.0.0
mv config/proxyx.json config/proxyz.json   # bila kamu punya file config lama
# ganti PROXYX_TOKEN -> PROXYZ_TOKEN di env / service kamu
# ganti `proxyx` -> `proxyz` di script / systemd unit / cron kamu
python -m proxyz doctor          # pastikan semuanya sehat
```

## Yang tidak berubah

- Perilaku semua perintah, format file `output/`, dan API Python
  (selain nama paket) tetap sama.
- Tidak ada data yang hilang: pool, blacklist, kesehatan sumber,
  dan key Webshare tidak disentuh rename ini.
