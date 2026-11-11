# Berkontribusi

Mau bantu? Gas. Caranya:

1. Fork, bikin branch, kerjain satu hal aja per PR.
2. Tiap fitur/bugfix baru harus ada tesnya. `pytest -q` harus hijau.
3. Jangan commit rahasia apa pun: API key, token, password,
   private key, file `config/webshare.json`, `output/`, `.env`.
4. Commit message yang jelas: `feat: ...`, `fix: ...`, `docs: ...`.

## Nambah sumber panen

Masukin URL-nya ke `config/sources.json` (kelompok `http` / `socks4` /
`socks5`). Pastiin formatnya `ip:port` per baris. Terus jalanin
`pytest -q` sama satu panen live buat mastiin sumber itu ngasih hasil.

## Nambah perintah

Tulis fungsinya di `proxyz/cli.py`, daftarin di `build_parser()`,
tambahin baris ke tabel perintah di README, tambahin tes di `tests/`.

## Yang nggak akan gue terima

- Pemecah captcha otomatis, farm akun massal, bypass Turnstile /
  anti-bot, dan segala bentuk pembuatan akun otomatis.
- Kode yang matiin verifikasi TLS, ngejalanin perintah dari server,
  atau nyimpen kredensial hardcode.
- Perubahan yang ngehapus data pengguna tanpa konfirmasi (misalnya
  `DELETE` tanpa backup).

## Nemu bug?

Buka issue pakai template bug report: sertain versi Proxyz
(`proxyz --version`), perintah yang dijalanin, output
`proxyz doctor`, sama log yang relevan. Jangan tempel API key/token.

Dengan ngirim PR, kamu setuju kontribusi kamu dilisensikan di bawah
lisensi MIT yang sama kayak proyek ini.
