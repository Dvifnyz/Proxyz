# Berkontribusi ke Proxyz

Terima kasih sudah mau berkontribusi! Panduan singkat ini supaya PR
kamu cepat diterima.

## Cara mulai

```bash
git clone https://github.com/Dvifnyz/Proxyz.git
cd Proxyz
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
python -m proxyz doctor
```

## Aturan dasar

1. **Satu PR, satu perubahan.** Jangan campur fitur baru dengan
   refactor besar.
2. **Tes dulu.** Setiap fitur/bugfix baru wajib disertai tes di
   `tests/` dan `pytest -q` harus hijau.
3. **Jangan merusak API publik** (lihat `docs/API.md`) tanpa diskusi
   dulu di issue.
4. **Jangan commit rahasia**: API key, token, password, private key,
   file `config/webshare.json`, `output/`, atau `.env`.
5. **Tulis commit yang jelas**, format: `type: ringkasan singkat`
   (`feat:`, `fix:`, `docs:`, `test:`, `chore:`). Contoh:
   `feat: tambah filter negara untuk SOCKS5`.

## Menambah sumber panen baru

1. Tambah URL ke `config/sources.json` (kelompok `http` / `socks4` /
   `socks5`).
2. Pastikan formatnya `ip:port` per baris (atau JSON `proxies` —
   lihat `proxyz/sources.py`).
3. Jalankan `pytest -q` dan satu panen live untuk memastikan sumber
   itu mengembalikan hasil.

## Menambah perintah CLI baru

1. Tulis fungsi di `proxyz/cli.py` + daftarkan di `build_parser()`.
2. Tambah baris ke tabel perintah di `README.md`.
3. Tambah tes di `tests/test_*.py`.

## Yang tidak akan diterima

- Pemecah captcha otomatis, farm akun massal, bypass Turnstile /
  anti-bot, dan segala bentuk pembuatan akun otomatis.
- Kode yang mematikan verifikasi TLS, mengeksekusi perintah dari
  server, atau menyimpan kredensial hardcode.
- Perubahan yang menghapus data pengguna tanpa konfirmasi
  (mis. `DELETE` tanpa backup).

## Lint & audit

Sebelum ngirim PR, jalanin ini (ruff sama vulture ada di extra `dev`):

```bash
ruff check proxyz/ tests/     # harus 0 error; aturannya di pyproject.toml
python -m vulture proxyz/ --min-confidence 80   # harus kosong
pytest -q                     # harus hijau
```

Dua aturan sengaja dimatiin di config (baca alasannya di pyproject):
`BLE001`/`S110` (error jaringan = proxy mati, bukan bug) sama
`S101` (assert adalah cara kerja pytest).

## Melaporkan bug

Pakai template issue "Bug report": sertakan versi Proxyz
(`proxyz --version`), perintah yang dijalankan, output
`proxyz doctor`, dan log yang relevan — **tanpa API key/token**.

## Lisensi

Dengan mengirim PR, kamu menyetujui kontribusi kamu dilisensikan
di bawah lisensi MIT yang sama dengan proyek ini.
