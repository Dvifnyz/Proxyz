# Kebijakan Keamanan

## Melaporkan kerentanan

**Jangan laporkan kerentanan lewat issue publik.**

Kirim laporan ke pemilik repo lewat GitHub
([buka issue privat / hubungi pemilik repo Dvifnyz](https://github.com/Dvifnyz))
dengan:

- deskripsi kerentanan dan dampaknya,
- langkah reproduksi (bila ada),
- versi Proxyz yang dipakai (`proxyz --version`).

Kami akan menanggapi dan memperbaiki secepatnya, lalu mencatatnya di
CHANGELOG.

## Yang sudah dijaga di Proxyz

- **Gateway hanya bind `127.0.0.1`** — tidak terekspos ke LAN/internet
  secara default.
- **Token opsional** (`PROXYZ_TOKEN`) untuk API & pemakaian proxy;
  token tidak pernah ditulis ke file config.
- **Rate limit** API (60/menit per IP) + audit log
  (`output/gateway-audit.jsonl`).
- **Verifikasi TLS tetap nyala** (system CA store); tidak ada
  `verify=False` / `ssl=False` di mana pun.
- **Updater aman**: update hanya via `pip` dari release GitHub —
  tidak pernah menjalankan perintah dari server.
- **API key Webshare** disimpan lokal mode `0600` dan tidak pernah
  di-commit (`.gitignore`).
- **Sinkronisasi 9Router** tidak pernah menghapus data orang lain:
  insert-only, backup dulu, `--ganti` hanya menghapus baris
  bertanda Proxyz/Proxyx.

## Yang di luar cakupan

- Proxy publik gratis itu sendiri (bukan milik Proxyz; kualitas dan
  keamanannya di luar kendali tool ini). Jangan kirim data sensitif
  lewat proxy publik yang tidak kamu kenal.
- Akun Webshare / Cloudflare pengguna (jaga API key kamu sendiri).
- Kerentanan di dependency pihak ketiga — laporkan ke proyek terkait,
  atau beri tahu kami supaya kami bisa menaikkan versinya.

## Hal yang tidak akan kami bangun

Pemecah captcha otomatis, farm akun massal, dan bypass anti-bot —
bukan karena tidak bisa, tapi karena itu membuat akun pengguna cepat
di-banned dan repo ini berisiko ditutup.
