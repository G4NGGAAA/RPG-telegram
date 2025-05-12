# Kerajaan Iblis - RPG Telegram Bots

Selamat datang di repository **Kerajaan Iblis**, sebuah game RPG berbasis bot Telegram dengan fitur lengkap dan pengalaman bermain yang seru di Termux.

---

## Bots dalam Repository

### 1. Main Player Bot (`kerajaan_iblis_bot.py`)

- Bot utama yang digunakan oleh para pemain.
- Fitur lengkap untuk bermain RPG: bertarung, perang/kolaborasi, berdagang, berburu, berpetualang.
- Sistem level hingga maksimal 100 untuk semua pemain biasa.
- Pemain dengan Telegram ID `6809803578` adalah **Dewa Iblis** dengan level tak terbatas (infinity), dapat menggunakan semua pedang, sihir, dan makhluk pendamping secara bersamaan.
- Makhluk pendamping dan pedang bermacam-macam tersedia, dengan keistimewaan khusus untuk Dewa Iblis.
- Fitur gift dan pengaturan kekuatan sihir saat menyerang.
- Kingdom yang kalah dalam perang akan mengalami pengurangan sumber daya sebesar 50%.
- Data pemain disimpan secara otomatis menggunakan sistem autosave.

### 2. Admin Control Bot (`kerajaan_iblis_admin_bot.py`)

- Bot khusus bagi admin / developer (ID Telegram: `6809803578`).
- Dapat melakukan reset semua data pemain.
- Menampilkan statistik game secara rinci.
- Memberikan item, buff, dan mengatur makhluk pendamping serta pedang untuk para pemain.
- Berbagi data yang sama dengan bot utama agar sinkron.
- Fitur pengaturan lengkap untuk mengelola game dan pemain.

---

## Fitur Utama

- **Sistem Level**: Maksimal level 100 untuk pemain biasa; Dewa Iblis memiliki level tak terbatas.
- **Item Eksklusif Dewa Iblis**: Magic sword khusus, makhluk mitologi legendaris, dan sihir pamungkas yang tidak dimiliki pemain lain.
- **Makhluk Pendamping**: Beragam makhluk dengan kekuatan berbeda, naik level mengikuti pemiliknya. Dewa Iblis dapat memiliki 2 makhluk mitologi sekaligus.
- **Sistem Sihir Dinamis**: Pemain dapat menggunakan berbagai sihir dengan tingkat kekuatan yang dapat diatur (misal: 50% kekuatan Fireball).
- **Perang/Kolaborasi Antar Kerajaan**: Pemain dapat bertarung bersama sekutu, dan mendapatkan efek pengurangan sumber daya pada kerajaan yang kalah.
- **Fitur Gift**: Memungkinkan pemain mengirim hadiah berupa emas kepada pemain lain.
- **Autosave**: Semua data game secara otomatis disimpan, menjaga kestabilan dan keberlanjutan game.

---

## Instalasi dan Penggunaan

1. Pasang Python di Termux:

```bash
pkg install python
pip install python-telegram-bot

