# Pendataan UMKM

Pendataan dan pembinaan UMKM. Prototipe independen untuk portofolio, bukan aplikasi resmi pemerintah.

## Fitur utama

- CRUD pelaku/usaha demonstrasi, bidang usaha, wilayah, skala dan status aktif/tidak aktif.
- CRUD program pembinaan, peserta unik per program serta pencatatan kehadiran.
- Pencarian, filter, statistik sesuai tampilan, ekspor CSV, arsip dan pemulihan usaha.
- Admin mengelola data induk/program; Admin dan Petugas mengelola usaha dan peserta. Tidak mengumpulkan NIK.

## Teknologi

Python 3.13, Flask, SQLite, HTML, CSS, JavaScript.

## Cara instalasi

~~~powershell
cd C:\laragon\www\pendataan-umkm
& 'C:\laragon\bin\python\python-3.13\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m core.users --role Admin
.\.venv\Scripts\python.exe -m core.users --role Petugas
~~~

Jika Python belum di PATH, gunakan lokasi python.exe yang terpasang. Kata sandi 12–200 karakter dimasukkan lewat prompt; tidak ada akun bawaan.

Lokasi Python pada perintah instalasi mengikuti Laragon di komputer ini; sesuaikan bila instalasi Python berada di lokasi lain.

## Cara menjalankan

~~~powershell
.\.venv\Scripts\python.exe run.py
~~~

Buka http://127.0.0.1:5431. Gunakan nama dan alamat contoh, tanpa identitas sensitif warga. SQLite di instance/app.sqlite dibuat otomatis dengan inisialisasi yang aman diulang. APP_INSTANCE dapat mengubah folder; set SECURE_COOKIE=1 untuk HTTPS.

Tes: .\.venv\Scripts\python.exe -m pytest.
