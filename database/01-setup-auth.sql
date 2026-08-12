-- ============================================================
-- SETUP LOGIN ADMIN & USER
-- Chatbot Prasarana Olahraga Tangsel
--
-- Jalankan di: Supabase Dashboard > SQL Editor > New Query
-- Aman dijalankan berulang kali (idempotent).
--
-- Tabel prasarana_olahraga, tarif_retribusi, history_chat_chatbot
-- TIDAK diubah strukturnya. Hanya ditambahkan proteksi RLS.
-- ============================================================


-- ------------------------------------------------------------
-- BAGIAN 1: Tabel profiles
--
-- Supabase sudah punya tabel auth.users bawaan (email, password
-- ter-hash, dll). Tabel itu tidak boleh diubah langsung, jadi
-- data tambahan kita (username & role) disimpan di sini dan
-- dihubungkan lewat kolom id.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.profiles (
    id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username   TEXT UNIQUE NOT NULL,
    nama       TEXT,
    role       TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE public.profiles IS
  'Data tambahan pengguna. role menentukan halaman tujuan setelah login.';


-- ------------------------------------------------------------
-- BAGIAN 2: Fungsi bantu cek admin
--
-- SECURITY DEFINER dipakai supaya fungsi ini bisa membaca tabel
-- profiles tanpa terjebak RLS-nya sendiri (kalau tidak, policy
-- yang memanggil fungsi ini akan memanggil dirinya sendiri terus
-- menerus / infinite recursion).
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'admin'
    );
$$;

-- Mengembalikan username orang yang sedang login, misal 'firad'.
CREATE OR REPLACE FUNCTION public.current_username()
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT username FROM public.profiles WHERE id = auth.uid();
$$;


-- ------------------------------------------------------------
-- BAGIAN 3: Trigger pembuat profil otomatis
--
-- Tiap ada pendaftaran baru di auth.users, baris profiles ikut
-- dibuat. Username diambil dari data yang dikirim saat signUp;
-- kalau kosong, dipakai bagian depan email sebagai cadangan.
--
-- role SELALU 'user' di sini. Admin tidak bisa dibuat lewat
-- form pendaftaran publik -- hanya lewat Bagian 7 di bawah.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    calon_username TEXT;
BEGIN
    calon_username := COALESCE(
        NULLIF(NEW.raw_user_meta_data->>'username', ''),
        split_part(NEW.email, '@', 1)
    );

    -- Jaga-jaga kalau username sudah dipakai orang lain:
    -- tambahkan potongan id supaya tetap unik dan tidak gagal.
    IF EXISTS (SELECT 1 FROM public.profiles WHERE username = calon_username) THEN
        calon_username := calon_username || '-' || substr(NEW.id::text, 1, 4);
    END IF;

    INSERT INTO public.profiles (id, username, nama, role)
    VALUES (
        NEW.id,
        calon_username,
        COALESCE(NEW.raw_user_meta_data->>'nama', calon_username),
        'user'
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ------------------------------------------------------------
-- BAGIAN 4: RLS tabel profiles
-- ------------------------------------------------------------

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profil sendiri bisa dibaca" ON public.profiles;
CREATE POLICY "profil sendiri bisa dibaca" ON public.profiles
    FOR SELECT TO authenticated
    USING (id = auth.uid() OR public.is_admin());

DROP POLICY IF EXISTS "profil sendiri bisa diubah" ON public.profiles;
CREATE POLICY "profil sendiri bisa diubah" ON public.profiles
    FOR UPDATE TO authenticated
    USING (id = auth.uid() OR public.is_admin())
    WITH CHECK (id = auth.uid() OR public.is_admin());

-- Hanya admin yang boleh menghapus akun orang lain.
DROP POLICY IF EXISTS "admin boleh hapus profil" ON public.profiles;
CREATE POLICY "admin boleh hapus profil" ON public.profiles
    FOR DELETE TO authenticated
    USING (public.is_admin());


-- ------------------------------------------------------------
-- BAGIAN 5: RLS tabel data prasarana
--
-- Semua orang (termasuk yang belum login) boleh MEMBACA, karena
-- chatbot harus tetap bisa menjawab pertanyaan.
-- Hanya admin yang boleh menambah, mengubah, dan menghapus.
--
-- Catatan penting: action server Rasa connect ke database pakai
-- user 'postgres' lewat psycopg2, bukan lewat API Supabase.
-- User postgres adalah superuser sehingga RLS tidak berlaku
-- untuknya. Jadi actions.py tetap jalan normal tanpa diubah.
-- ------------------------------------------------------------

ALTER TABLE public.prasarana_olahraga ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "prasarana bisa dibaca siapa saja" ON public.prasarana_olahraga;
CREATE POLICY "prasarana bisa dibaca siapa saja" ON public.prasarana_olahraga
    FOR SELECT TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "admin kelola prasarana" ON public.prasarana_olahraga;
CREATE POLICY "admin kelola prasarana" ON public.prasarana_olahraga
    FOR ALL TO authenticated
    USING (public.is_admin())
    WITH CHECK (public.is_admin());


ALTER TABLE public.tarif_retribusi ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tarif bisa dibaca siapa saja" ON public.tarif_retribusi;
CREATE POLICY "tarif bisa dibaca siapa saja" ON public.tarif_retribusi
    FOR SELECT TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "admin kelola tarif" ON public.tarif_retribusi;
CREATE POLICY "admin kelola tarif" ON public.tarif_retribusi
    FOR ALL TO authenticated
    USING (public.is_admin())
    WITH CHECK (public.is_admin());


-- Tabel prasarana_olahraga_kolam_renang saat ini TIDAK dipakai
-- oleh actions.py (data kolam renang diambil dari prasarana_olahraga
-- + tarif_retribusi). Tetap diberi RLS karena tabel tanpa RLS bisa
-- ditulis siapa saja yang punya anon key, dan anon key terpasang
-- terbuka di front-end. Jangan dihapus sebelum dipastikan tidak
-- ada yang memakainya.

ALTER TABLE public.prasarana_olahraga_kolam_renang ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "kolam bisa dibaca siapa saja" ON public.prasarana_olahraga_kolam_renang;
CREATE POLICY "kolam bisa dibaca siapa saja" ON public.prasarana_olahraga_kolam_renang
    FOR SELECT TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "admin kelola kolam" ON public.prasarana_olahraga_kolam_renang;
CREATE POLICY "admin kelola kolam" ON public.prasarana_olahraga_kolam_renang
    FOR ALL TO authenticated
    USING (public.is_admin())
    WITH CHECK (public.is_admin());


-- Tabel 'events' adalah tracker store bawaan Rasa, bukan buatan
-- tim. JANGAN diberi RLS -- bisa mengganggu jalannya bot.


-- ------------------------------------------------------------
-- BAGIAN 6: RLS tabel riwayat chat
--
-- Kolom session_id sudah ada dan diisi oleh log_chat() di
-- actions.py dengan nilai tracker.sender_id. Setelah index.html
-- diubah, nilainya menjadi 'user-<username>', misal 'user-firad'.
--
-- Policy di bawah memanfaatkan pola itu: user hanya bisa melihat
-- baris yang session_id-nya cocok dengan username miliknya.
-- Struktur tabel tidak perlu diubah sama sekali.
-- ------------------------------------------------------------

ALTER TABLE public.history_chat_chatbot ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user lihat riwayat sendiri" ON public.history_chat_chatbot;
CREATE POLICY "user lihat riwayat sendiri" ON public.history_chat_chatbot
    FOR SELECT TO authenticated
    USING (
        public.is_admin()
        OR session_id = 'user-' || public.current_username()
    );


-- ------------------------------------------------------------
-- BAGIAN 7: Mengangkat akun menjadi admin
--
-- Urutannya: daftar dulu lewat login.html seperti user biasa,
-- baru jalankan perintah ini untuk menaikkan rolenya.
-- Ganti alamat email di bawah dengan email admin yang asli.
-- ------------------------------------------------------------

-- UPDATE public.profiles
-- SET role = 'admin'
-- WHERE id = (SELECT id FROM auth.users WHERE email = 'admin@contoh.com');


-- ------------------------------------------------------------
-- BAGIAN 8: Pemeriksaan hasil
-- Jalankan setelah semua di atas selesai.
-- ------------------------------------------------------------

-- Daftar seluruh pengguna beserta rolenya:
-- SELECT p.username, p.nama, p.role, u.email, p.created_at
-- FROM public.profiles p
-- JOIN auth.users u ON u.id = p.id
-- ORDER BY p.created_at DESC;

-- Memastikan RLS sudah aktif di keempat tabel:
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN ('profiles','prasarana_olahraga',
--                     'tarif_retribusi','history_chat_chatbot');
