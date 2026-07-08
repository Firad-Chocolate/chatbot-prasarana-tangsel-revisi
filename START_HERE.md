# MULAI DARI SINI

Paket ini sudah lengkap dan siap deploy. Ikuti urutan ini dari atas ke bawah.

## Checklist urutan kerja

- [ ] **1. Rotate kredensial lama** (password Supabase + API key Cloudinary yang
      pernah bocor di GitHub public) — lihat `DEPLOYMENT_GUIDE.md` Langkah 0.
      **Wajib dilakukan pertama, sebelum apapun.**
- [ ] **2. Pastikan VPS DewaBiz aktif**, catat IP + username + password, OS
      pilih **Ubuntu 22.04**.
- [ ] **3. Upload `chatbot-prasarana-tangsel-fixed.zip` ini ke VPS** via SCP —
      `DEPLOYMENT_GUIDE.md` Langkah 1-3.
- [ ] **4. Setup Docker & jalankan container** — Langkah 2, 4-5.
- [ ] **5. Import data prasarana** (`database/import_prasarana.sql`) ke Supabase
      — Langkah 5.5.
- [ ] **6. Tes chatbot** dari VPS — Langkah 6.
- [ ] **7. Buka firewall** — Langkah 7.
- [ ] **8. (Opsional) Setup domain + HTTPS** — Langkah 8.
- [ ] **9. Sambungkan widget chat (frontend) ke URL VPS** — Langkah 9.

## Isi paket ini

| File/Folder | Fungsi |
|---|---|
| `DEPLOYMENT_GUIDE.md` | Panduan lengkap step-by-step, baca ini utamanya |
| `CHANGES_SUMMARY.md` | Daftar semua perbaikan yang sudah dilakukan dari repo asli |
| `docker-compose.yml`, `Dockerfile`, `Dockerfile.actions` | Konfigurasi deploy Docker |
| `.env.example` | Template kredensial — copy jadi `.env`, isi dengan kredensial ASLI |
| `database/import_prasarana.sql` | Data 15 prasarana olahraga, siap paste ke Supabase SQL Editor |
| `scripts/import_excel_to_db.py` | Script buat import data Excel baru di masa depan |
| `deploy/nginx-rasa.conf` | Config Nginx kalau nanti pakai domain + HTTPS |
| `actions/`, `data/`, `domain.yml`, `config.yml` | Kode & training data chatbot (tidak diubah logikanya) |

## Yang paling penting diingat
Password database & API key yang lama **sudah pernah terlihat publik** di
GitHub. Sebelum server ini live, wajib ganti dulu ke yang baru (Langkah 0 di
`DEPLOYMENT_GUIDE.md`). Ini bukan langkah opsional.
