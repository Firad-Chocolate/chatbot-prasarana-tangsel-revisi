/**
 * Konfigurasi Supabase — dipakai bersama oleh login.html, index.html, admin.html.
 *
 * Dua nilai di bawah memang dirancang untuk publik dan aman terlihat di
 * browser. Yang melindungi data bukan kerahasiaan key ini, melainkan
 * Row Level Security di database (lihat database/01-setup-auth.sql).
 * Key service_role TIDAK BOLEH diletakkan di file ini.
 */
const SUPABASE_URL = "https://vvtxhftvgpkbsjslyrdo.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ2dHhoZnR2Z3BrYnNqc2x5cmRvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMxNzM1MDUsImV4cCI6MjA5ODc0OTUwNX0.SiqWdRwlTJAweKDk5BoPu1lCmJtz_ypakmJWou1sQHA";

const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

/** Semua halaman berada di bawah /chat/ karena begitu konfigurasi Nginx. */
const BASE = "/chat/";

/**
 * Mengambil sesi + profil orang yang sedang login.
 * Mengembalikan null kalau belum login.
 */
async function getSesiProfil() {
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return null;

    const { data: profil, error } = await sb
        .from("profiles")
        .select("username, nama, role")
        .eq("id", session.user.id)
        .single();

    if (error || !profil) return null;
    return { session, profil };
}

/** Menendang pengunjung ke halaman yang sesuai dengan perannya. */
async function wajibLogin(peranWajib) {
    const hasil = await getSesiProfil();
    if (!hasil) {
        window.location.replace(BASE + "login.html");
        return null;
    }
    if (peranWajib === "admin" && hasil.profil.role !== "admin") {
        window.location.replace(BASE + "index.html");
        return null;
    }
    return hasil;
}

async function keluar() {
    await sb.auth.signOut();
    window.location.replace(BASE + "login.html");
}
