# Panduan Deploy Chatbot Rasa ke VPS (Depa Cloud / VPS murah sejenis)

Panduan ini asumsi VPS Ubuntu 22.04, akses root via SSH, dan kamu sudah rotate
kredensial (lihat Langkah 0 — WAJIB dilakukan lebih dulu).

## ⚠️ Peringatan spek VPS

Rasa (khususnya `DIETClassifier` dan `TEDPolicy` yang dipakai di `config.yml`)
berbasis TensorFlow dan cukup rakus RAM saat loading model — idealnya **minimal
2GB RAM**. Kalau paket VPS 50 ribuan kamu cuma dapat 1GB RAM, chatbot masih bisa
jalan tapi berisiko OOM (out of memory) terutama saat container action-server dan
rasa-server jalan bersamaan. Mitigasi ada di Langkah 2 (swap file).

---

## Langkah 0 — Rotate kredensial yang sudah bocor (WAJIB, sebelum lanjut)

Password database & API key lama sudah pernah tampil publik di GitHub, jadi
harus diganti dulu:

1. Login ke dashboard Supabase → Project Settings → Database → reset password
2. Login ke dashboard Cloudinary → Settings → Security → regenerate API secret
3. Catat kredensial baru ini, akan dipakai di Langkah 5

---

## Langkah 1 — Upload file ke VPS

Karena kamu sudah punya file `chatbot-prasarana-tangsel-fixed.zip` hasil download,
paling simpel upload langsung lewat SCP dari komputer lokal (bukan di VPS):

**Windows (PowerShell):**
```powershell
scp chatbot-prasarana-tangsel-fixed.zip root@IP_VPS_KAMU:/opt/
```

**Mac/Linux (Terminal):**
```bash
scp chatbot-prasarana-tangsel-fixed.zip root@IP_VPS_KAMU:/opt/
```

Masukkan password VPS kamu saat diminta. File akan tersalin ke `/opt/` di VPS.

> Alternatif: kalau kamu lebih suka pakai GitHub (misalnya supaya gampang update
> ke depannya), push dulu foldernya ke repo GitHub kamu, lalu nanti di Langkah 3
> pakai `git clone` sebagai ganti extract zip.

---

## Langkah 2 — Setup awal VPS

SSH ke VPS:
```bash
ssh root@IP_VPS_KAMU
```

Update sistem:
```bash
apt update && apt upgrade -y
```

**Buat swap file** (penting kalau RAM VPS kecil, 1-2GB):
```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Install Docker & Docker Compose plugin:
```bash
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
docker --version
docker compose version
```

---

## Langkah 3 — Extract file di VPS

```bash
cd /opt
apt install -y unzip
unzip chatbot-prasarana-tangsel-fixed.zip -d chatbot-prasarana-tangsel
cd chatbot-prasarana-tangsel
```

---

## Langkah 4 — Siapkan file `.env`

```bash
cp .env.example .env
nano .env
```

Isi dengan kredensial **baru** hasil rotate di Langkah 0:
```
DB_HOST=xxxxx.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=password_baru_kamu

CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```
Simpan (`Ctrl+O`, Enter, `Ctrl+X`).

---

## Langkah 5 — Build & jalankan container

```bash
docker compose up -d --build
```

Proses build pertama kali agak lama (base image Rasa besar, ±1-2GB download).
Setelah selesai, cek status:
```bash
docker compose ps
docker compose logs -f rasa
```
Tunggu sampai log menunjukkan Rasa server aktif di port 5005 (biasanya baris
`Rasa server is up and running`).

---

## Langkah 5.5 — Import data prasarana ke database

Repo ini sudah menyertakan data prasarana olahraga siap import di
`database/import_prasarana.sql` (15 lokasi, sudah dicocokkan dengan training
data chatbot).

1. Login ke [supabase.com](https://supabase.com) → project kamu → **SQL Editor**
2. New Query → paste seluruh isi `database/import_prasarana.sql` → **Run**
3. Otomatis bikin tabel `prasarana_olahraga` (kalau belum ada) dan isi 15 data

Aman dijalankan berulang kali — tidak akan menduplikasi data (pakai
`ON CONFLICT DO UPDATE`).

Kalau nanti ada data baru dalam format Excel dengan struktur kolom yang sama
(Nama Prasarana, Olahraga, Alamat, Kecamatan, Google maps link, Status, Link
Gambar 1-3), tinggal jalankan dari komputer lokal (bukan di VPS):
```bash
pip install -r scripts/requirements-import.txt --break-system-packages
python scripts/import_excel_to_db.py path/ke/Data_Baru.xlsx
```

---

## Langkah 6 — Tes chatbot dari VPS

```bash
curl -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender": "test", "message": "halo"}'
```
Kalau muncul balasan JSON dari bot, berarti Rasa server + action server sudah
nyambung dengan benar.

---

## Langkah 7 — Buka akses dari luar (firewall)

```bash
ufw allow 22/tcp
ufw allow 5005/tcp
ufw enable
```
Sekarang bot bisa diakses dari `http://IP_VPS_KAMU:5005`.

---

## Langkah 8 (opsional, disarankan) — Domain + HTTPS via Nginx

Kalau kamu punya domain/subdomain, arahkan DNS A record ke IP VPS, lalu:

```bash
apt install -y nginx certbot python3-certbot-nginx
cp deploy/nginx-rasa.conf /etc/nginx/sites-available/chatbot-rasa
nano /etc/nginx/sites-available/chatbot-rasa   # sesuaikan server_name
ln -s /etc/nginx/sites-available/chatbot-rasa /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

certbot --nginx -d chatbot.domainkamu.com
```
Setelah ini, bot bisa diakses via `https://chatbot.domainkamu.com` (port 5005
gak perlu dibuka publik lagi, tutup saja: `ufw delete allow 5005/tcp`).

---

## Langkah 9 — Sambungkan frontend (Netlify) ke backend VPS

Di file `ui/rasa.html` dan `index.html`, ganti:
```js
socketUrl: "GANTI_DENGAN_URL_VPS_KAMU",
```
menjadi URL VPS/domain kamu, misalnya `"https://chatbot.domainkamu.com"`.

Di `credentials.yml`, pastikan `cors_allowed_origins` mengandung domain Netlify
frontend kamu (sudah ada `chatbot-prasarana-tangsel.netlify.app` — sesuaikan
kalau domainnya beda). Setelah edit, push ulang & restart container:
```bash
docker compose up -d --build rasa
```

---

## Maintenance sehari-hari

| Kebutuhan | Command |
|---|---|
| Lihat log | `docker compose logs -f rasa` atau `-f action-server` |
| Restart | `docker compose restart` |
| Update kode (upload file baru) | lihat "Cara update kode" di bawah |
| Cek pemakaian RAM | `docker stats` |
| Stop semua | `docker compose down` |

### Cara update kode (tanpa GitHub)
Kalau ada perubahan file (misal model baru hasil training ulang, atau ada
perbaikan kode):
1. Dari komputer lokal, upload file yang berubah lewat SCP, contoh:
   ```bash
   scp -r models/nama-model-baru.tar.gz root@IP_VPS_KAMU:/opt/chatbot-prasarana-tangsel/models/
   ```
2. Di VPS, rebuild container yang terpengaruh:
   ```bash
   cd /opt/chatbot-prasarana-tangsel
   docker compose up -d --build rasa
   ```

> Kalau ke depannya project makin sering di-update, pertimbangkan pindah ke
> alur GitHub (`git push` di lokal, `git pull` di VPS) — lebih cepat dan
> tercatat historinya. Tapi untuk sekarang, SCP manual sudah cukup.

---

# ALTERNATIF: Deploy via Railway + Netlify (bukan VPS)

Repo ini juga sudah disiapkan untuk jalur ini (`railway.toml` + `netlify.toml`).
**Penting:** ini bukan gratis permanen — cek dulu bagian "Soal biaya" di bawah.

## Soal biaya (baca dulu sebelum mulai)
- Railway: trial 30 hari dengan kredit $5, setelah itu **wajib** upgrade ke Hobby
  ($5/bulan) atau lanjut di plan gratis dengan resource sangat kecil (0.5GB RAM,
  kredit cuma $1/bulan) — kemungkinan kurang buat Rasa+TensorFlow yang butuh RAM
  lebih besar. Realistisnya, biar stabil kamu perlu bayar ~$5/bulan (lebih mahal
  dari VPS 50rb/bulan kamu).
- Netlify: gratis untuk hosting frontend statis (widget chat), ini bagian yang
  memang cocok dipakai gratis.

## Langkah A — Deploy backend (Rasa + action server) ke Railway

1. Daftar di [railway.com](https://railway.com), connect akun GitHub
2. New Project → Deploy from GitHub repo → pilih repo `chatbot-prasarana-tangsel`
3. Railway otomatis detect `railway.toml` dan build pakai `Dockerfile`
4. Di tab **Variables**, tambahkan environment variable:
   ```
   ACTION_ENDPOINT_URL=http://127.0.0.1:5055/webhook
   DB_HOST=xxxxx.supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=password_baru_hasil_rotate
   ```
   (Railway otomatis inject `$PORT` sendiri, gak perlu diisi manual)
5. Deploy akan jalan otomatis. Setelah selesai, di tab **Settings → Networking**,
   klik **Generate Domain** untuk dapat URL publik (contoh:
   `xxxxx.up.railway.app`)
6. Tes: `curl -X POST https://xxxxx.up.railway.app/webhooks/rest/webhook -H "Content-Type: application/json" -d '{"sender":"test","message":"halo"}'`

## Langkah B — Deploy frontend ke Netlify

1. Update dulu `socketUrl` di `index.html` / `ui/rasa.html` jadi URL Railway dari
   Langkah A (`https://xxxxx.up.railway.app`), commit & push ke GitHub
2. Daftar di [netlify.com](https://netlify.com), connect akun GitHub
3. Add new site → Import from Git → pilih repo yang sama
4. Build command: kosongkan. Publish directory: `.` (root)
5. Deploy. Netlify kasih URL seperti `https://nama-acak.netlify.app`
6. Update `credentials.yml` bagian `cors_allowed_origins` dengan URL Netlify ini
   (kalau beda dari yang sudah ada), commit & push — Railway akan auto-redeploy

## Kapan pilih Railway+Netlify vs VPS?

- **Railway+Netlify**: kalau kamu gak mau pusing setup server manual (SSH,
  Docker, Nginx), dan gak masalah bayar ~$5/bulan (~Rp80rb) setelah trial habis
- **VPS**: kalau budget mepet 50rb/bulan dan gak masalah setup manual sendiri
  (sudah dipandu lengkap di bagian atas dokumen ini)

