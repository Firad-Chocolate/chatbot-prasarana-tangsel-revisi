# Ringkasan Perbaikan Repo

## 🚨 Keamanan (paling penting)
- **Dihapus** password database Supabase yang hardcoded di `actions/db.py`
- **Dihapus** file `main.py` — file sample tidak terpakai yang mengandung API key Cloudinary
- `db.py` sekarang **wajib** ambil kredensial dari environment variable; kalau tidak diset, aplikasi gagal start dengan pesan error yang jelas (bukan diam-diam pakai kredensial lama)
- Ditambahkan `.env.example` (template) dan `.gitignore` (agar `.env` asli tidak pernah ke-commit)

> ⚠️ Password & API key lama yang sudah pernah ter-push ke GitHub public **wajib
> di-rotate** (diganti yang baru) — lihat Langkah 0 di `DEPLOYMENT_GUIDE.md`.
> Ini bukan opsional, karena kredensial lama sudah terlanjur terlihat publik.

## 🧹 Kebersihan repo
- Folder `models/` dari 37 file (~900MB) dirampingkan jadi 1 file model terbaru (~25MB)
- Folder `root/` yang salah tempat (isinya `.dockerignore` yang nyasar) dihapus, filenya dipindah ke lokasi yang benar
- `requirements.txt` — hapus baris duplikat

## 🐳 Deploy ke VPS
- **Baru:** `docker-compose.yml` — orkestrasi Rasa server + action server dalam satu perintah (`docker compose up -d`), sebelumnya konfigurasi hanya menyasar Railway (PaaS), bukan VPS generic
- `endpoints.yml` — action_endpoint diarahkan ke nama service Docker (`action-server`) bukan `127.0.0.1`, supaya kedua container bisa saling connect
- `Dockerfile` — hapus reinstall paket `rasa`/`rasa-sdk` yang berisiko bikin mismatch versi dengan model yang sudah di-train
- `Dockerfile.actions` — pakai `requirements.txt` langsung, konsisten dengan dependency yang terdefinisi
- **Baru:** `deploy/nginx-rasa.conf` — konfigurasi reverse proxy siap pakai untuk domain + HTTPS
- **Baru:** `DEPLOYMENT_GUIDE.md` — panduan lengkap step-by-step dari setup VPS kosong sampai bot live

## 🖥️ Frontend
- `ui/rasa.html` dan `index.html` — URL backend yang tadinya hardcode ke Railway lama/localhost, diganti jadi placeholder jelas (`GANTI_DENGAN_URL_VPS_KAMU`) supaya gak lupa disesuaikan setelah VPS live

## 📊 Data
- **Baru:** `database/import_prasarana.sql` — 15 data prasarana olahraga siap import ke Supabase (paste & run di SQL Editor), aman dijalankan berulang
- **Baru:** `scripts/import_excel_to_db.py` — script reusable untuk import data Excel baru di masa depan tanpa perlu generate SQL manual

## 📋 Navigasi
- **Baru:** `START_HERE.md` — checklist urutan kerja dari awal sampai akhir, baca ini pertama kali

## Yang TIDAK diubah (sengaja)
- `data/nlu.yml`, `data/stories.yml`, `data/rules.yml`, `domain.yml`, `config.yml` — logika & training data chatbot tidak disentuh, murni technical debt & security fix
- `railway.toml`, `netlify.toml` — dibiarkan ada kalau-kalau suatu saat mau kembali pakai Railway/Netlify, tidak dipakai di jalur deploy VPS ini
