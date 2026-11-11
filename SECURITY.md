# Keamanan

Nemu celah keamanan? Jangan buka issue publik. Hubungi pemilik repo
lewat GitHub ([Dvifnyz](https://github.com/Dvifnyz)), sertain
deskripsi sama cara reproduksinya.

## Yang udah dijaga

- Gateway cuma bind `127.0.0.1` — nggak terekspos ke LAN/internet.
- Token nggak pernah ditulis ke file config.
- API dibatasi 60 request/menit per IP, aktivitas dicatat di
  `output/gateway-audit.jsonl`.
- Verifikasi TLS tetap nyala (system CA store). Nggak ada
  `verify=False` / `ssl=False` di mana pun.
- Updater cuma lewat `pip` dari release GitHub — nggak pernah
  ngejalanin perintah dari server.
- API key Webshare disimpen lokal mode `0600`, nggak pernah
  di-commit (`.gitignore`).
- Sync 9Router nggak pernah ngehapus data orang lain: insert-only,
  backup dulu, `--ganti` cuma ngehapus baris bertanda Proxyz/Proxyx.

## Yang di luar tanggung jawab tool ini

- Proxy publik gratis itu sendiri (bukan punya Proxyz). Jangan kirim
  data sensitif lewat proxy yang nggak kamu kenal.
- Akun Webshare / Cloudflare kamu — jaga API key kamu sendiri.
- Celah di dependency pihak ketiga — laporin ke proyek terkait,
  atau kasih tau gue biar versinya dinaikin.

## Yang nggak akan gue bangun

Pemecah captcha otomatis, farm akun massal, dan bypass anti-bot.
Bukan karena nggak bisa, tapi karena itu bikin akun pengguna cepet
di-ban dan repo ini berisiko ditutup.
