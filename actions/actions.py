"""
Custom actions untuk chatbot Prasarana Olahraga Pemerintah Kota Tangerang Selatan.
Setiap action mengambil data langsung dari database PostgreSQL.

Update:
- Tambah ActionCariPrasaranaOlahragaKecamatan (filter olahraga + kecamatan sekaligus)
- Perbaikan format respons agar lebih menarik dan informatif
- Foto menggunakan link Cloudinary (direct URL, tanpa konversi)
"""

from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from .db import query_db, execute_db

ERROR_DB = (
    "⚠️ Maaf, saat ini saya tidak bisa mengakses data prasarana karena ada "
    "gangguan koneksi ke database. Silakan coba lagi beberapa saat lagi."
)

SEPARATOR = "─────────────────────"


def get_entity_fresh(tracker: Tracker, entity_name: str) -> Optional[str]:
    """
    Mengambil nilai entity langsung dari pesan TERAKHIR yang dikirim user
    (tracker.latest_message), BUKAN dari slot.

    Ini sengaja dipakai menggantikan tracker.get_slot() karena slot dengan
    mapping 'from_entity' di Rasa TIDAK otomatis kosong kalau entity tidak
    terdeteksi di pesan terbaru — nilainya tetap nyangkut dari pesan
    sebelumnya. Akibatnya kalau user salah ketik ('voly' alih-alih 'voli')
    sehingga entity gagal ter-deteksi, bot malah menjawab pakai topik
    pertanyaan SEBELUMNYA (misal kolam renang) alih-alih bilang tidak paham.

    Dengan membaca langsung dari tracker.latest_message, setiap pesan baru
    selalu dievaluasi bersih tanpa terpengaruh riwayat percakapan.
    """
    entities = tracker.latest_message.get("entities", []) if tracker.latest_message else []
    for e in entities:
        if e.get("entity") == entity_name:
            return e.get("value")
    return None


def kirim_foto(dispatcher: CollectingDispatcher, row: Dict[str, Any]) -> None:
    """
    Mengirim foto 1, 2, dan 3 dari satu baris data prasarana ke chat widget.
    Link Cloudinary sudah berupa direct URL — langsung dipakai tanpa konversi.
    """
    for kolom in ("link_gambar_1", "link_gambar_2", "link_gambar_3"):
        url = row.get(kolom)
        if url:
            dispatcher.utter_message(image=url)


def log_chat(tracker: Tracker, jawaban_bot: str) -> None:
    """
    Mencatat setiap percakapan (pesan user + jawaban bot) ke tabel
    history_chat_chatbot di Supabase. Semua percakapan digabung dalam satu
    tabel (tidak dipisah per user), sesuai permintaan.
    Kegagalan logging tidak boleh mengganggu jalannya chatbot, jadi error
    apa pun di sini hanya dicatat ke log server, tidak ditampilkan ke user.
    """
    try:
        session_id = tracker.sender_id or "unknown"
        pesan_user = tracker.latest_message.get("text") or ""
        gabungan = f"User: {pesan_user}\nBot: {jawaban_bot}"
        execute_db(
            "INSERT INTO history_chat_chatbot (session_id, respon_chatbot, tanggal_chat) "
            "VALUES (%s, %s, NOW());",
            (session_id, gabungan),
        )
    except Exception:
        pass


def format_harga_block(r: Dict[str, Any]) -> str:
    """
    Menyusun teks blok harga + nomor telepon pengelola dari satu baris data
    prasarana. Ada 2 kemungkinan sumber data harga:
    1. Kolom harga_member_sesi_1/2, harga_non_member_sesi_1/2 di tabel
       prasarana_olahraga (dipakai kebanyakan cabang olahraga).
    2. Tabel tarif_retribusi terpisah, dikelompokkan Pengunjung/Rombongan
       dengan tipe hari weekday/weekend (khusus dipakai kolam renang).
    Mengembalikan string kosong kalau kedua sumber sama sekali tidak ada data
    (supaya action tidak menampilkan blok kosong).
    """
    harga_items = []
    if r.get("harga_member_sesi_1"):
        harga_items.append(f"  • Member Sesi 1    : Rp{r['harga_member_sesi_1']:,}".replace(",", "."))
    if r.get("harga_member_sesi_2"):
        harga_items.append(f"  • Member Sesi 2    : Rp{r['harga_member_sesi_2']:,}".replace(",", "."))
    if r.get("harga_non_member_sesi_1"):
        harga_items.append(f"  • Non-Member Sesi 1: Rp{r['harga_non_member_sesi_1']:,}".replace(",", "."))
    if r.get("harga_non_member_sesi_2"):
        harga_items.append(f"  • Non-Member Sesi 2: Rp{r['harga_non_member_sesi_2']:,}".replace(",", "."))

    blok = ""

    if harga_items:
        blok = f"💰 *Daftar Harga:*\n🏷️ {r.get('olahraga', '')}:\n" + "\n".join(harga_items)
    elif r.get("id"):
        # Kolom sederhana kosong -> coba cek tabel tarif_retribusi (khusus kolam renang)
        tarif_rows = query_db(
            """
            SELECT jenis_pengunjung, kategori, tipe_hari, keterangan_tambahan, tarif, satuan
            FROM tarif_retribusi
            WHERE prasarana_id = %s
            ORDER BY jenis_pengunjung, id;
            """,
            (r["id"],),
        )
        if tarif_rows:
            baris_pengunjung = []
            baris_rombongan = []
            for t in tarif_rows:
                harga = f"Rp{t['tarif']:,}".replace(",", ".")
                if t["jenis_pengunjung"] == "Pengunjung":
                    hari = f" ({t['tipe_hari']})" if t["tipe_hari"] else ""
                    baris_pengunjung.append(f"  • {t['kategori']}{hari}: {harga} / {t['satuan']}")
                else:
                    ket = f" ({t['keterangan_tambahan']})" if t["keterangan_tambahan"] else ""
                    baris_rombongan.append(f"  • {t['kategori']}{ket}: {harga} / {t['satuan']}")

            blok = "💰 *Daftar Harga:*\n"
            if baris_pengunjung:
                blok += "👤 Pengunjung:\n" + "\n".join(baris_pengunjung) + "\n"
            if baris_rombongan:
                blok += "👥 Rombongan:\n" + "\n".join(baris_rombongan)
            blok = blok.strip()

    if not blok:
        return ""

    if r.get("nomor_pengelola"):
        blok += f"\n📞 Nomor Telepon Pengelola: {r['nomor_pengelola']}"

    return blok


class ActionCariPrasaranaOlahraga(Action):
    """Mencari prasarana berdasarkan jenis olahraga saja."""

    def name(self) -> Text:
        return "action_cari_prasarana_olahraga"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        olahraga: Optional[str] = get_entity_fresh(tracker, "olahraga")

        if not olahraga:
            dispatcher.utter_message(response="utter_ask_olahraga")
            return []

        rows = query_db(
            """
            SELECT id, nama_prasarana, olahraga, alamat, kecamatan, google_maps_link,
                   nomor_pengelola, harga_member_sesi_1, harga_member_sesi_2,
                   harga_non_member_sesi_1, harga_non_member_sesi_2,
                   link_gambar_1, link_gambar_2, link_gambar_3
            FROM prasarana_olahraga
            WHERE (olahraga ILIKE %s OR nama_prasarana ILIKE %s) AND status ILIKE 'aktif'
            ORDER BY kecamatan, nama_prasarana;
            """,
            (f"%{olahraga}%", f"%{olahraga}%"),
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(
                text=f"😔 Maaf, untuk saat ini prasarana *{olahraga}* belum tersedia."
            )
            return []

        dispatcher.utter_message(
            text=(
                f"🔍 Ditemukan *{len(rows)} prasarana* untuk olahraga *{olahraga.title()}* "
                f"di Kota Tangerang Selatan:\n{SEPARATOR}"
            )
        )

        for i, r in enumerate(rows, 1):
            pesan = (
                f"*{i}. {r['nama_prasarana']}*\n"
                f"📍 {r['alamat']}\n"
                f"🏘️ Kec. {r['kecamatan']}\n"
                f"🗺️ {r['google_maps_link']}"
            )
            blok_harga = format_harga_block(r)
            if blok_harga:
                pesan += f"\n{SEPARATOR}\n{blok_harga}"
            dispatcher.utter_message(text=pesan)
            kirim_foto(dispatcher, r)

        log_chat(tracker, f"[{len(rows)} prasarana olahraga '{olahraga}' ditampilkan]")
        return []


class ActionCariPrasaranaKecamatan(Action):
    """Mencari semua prasarana berdasarkan kecamatan saja."""

    def name(self) -> Text:
        return "action_cari_prasarana_kecamatan"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        kecamatan: Optional[str] = get_entity_fresh(tracker, "kecamatan")

        if not kecamatan:
            dispatcher.utter_message(response="utter_ask_kecamatan")
            return []

        rows = query_db(
            """
            SELECT id, nama_prasarana, olahraga, alamat, google_maps_link,
                   nomor_pengelola, harga_member_sesi_1, harga_member_sesi_2,
                   harga_non_member_sesi_1, harga_non_member_sesi_2,
                   link_gambar_1, link_gambar_2, link_gambar_3
            FROM prasarana_olahraga
            WHERE kecamatan ILIKE %s AND status ILIKE 'aktif'
            ORDER BY nama_prasarana;
            """,
            (f"%{kecamatan}%",),
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(
                text=f"😔 Maaf, belum ada data prasarana di Kecamatan *{kecamatan}*."
            )
            return []

        dispatcher.utter_message(
            text=(
                f"🏘️ Ditemukan *{len(rows)} prasarana* di Kecamatan *{kecamatan.title()}*:\n"
                f"{SEPARATOR}"
            )
        )

        for i, r in enumerate(rows, 1):
            pesan = (
                f"*{i}. {r['nama_prasarana']}*\n"
                f"⚽ {r['olahraga']}\n"
                f"📍 {r['alamat']}\n"
                f"🗺️ {r['google_maps_link']}"
            )
            blok_harga = format_harga_block(r)
            if blok_harga:
                pesan += f"\n{SEPARATOR}\n{blok_harga}"
            dispatcher.utter_message(text=pesan)
            kirim_foto(dispatcher, r)

        log_chat(tracker, f"[{len(rows)} prasarana di kecamatan '{kecamatan}' ditampilkan]")
        return []


class ActionCariPrasaranaOlahragaKecamatan(Action):
    """Mencari prasarana berdasarkan olahraga DAN kecamatan sekaligus.
    Contoh: lapangan futsal di Pamulang, tenis di Ciputat."""

    def name(self) -> Text:
        return "action_cari_prasarana_olahraga_kecamatan"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        olahraga: Optional[str] = get_entity_fresh(tracker, "olahraga")
        kecamatan: Optional[str] = get_entity_fresh(tracker, "kecamatan")

        if not olahraga:
            dispatcher.utter_message(response="utter_ask_olahraga")
            return []

        if not kecamatan:
            dispatcher.utter_message(response="utter_ask_kecamatan")
            return []

        rows = query_db(
            """
            SELECT id, nama_prasarana, olahraga, alamat, kecamatan, google_maps_link,
                   nomor_pengelola, harga_member_sesi_1, harga_member_sesi_2,
                   harga_non_member_sesi_1, harga_non_member_sesi_2,
                   link_gambar_1, link_gambar_2, link_gambar_3
            FROM prasarana_olahraga
            WHERE olahraga ILIKE %s
              AND kecamatan ILIKE %s
              AND status ILIKE 'aktif'
            ORDER BY nama_prasarana;
            """,
            (f"%{olahraga}%", f"%{kecamatan}%"),
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(
                text=(
                    f"😔 Maaf, tidak ada prasarana *{olahraga}* "
                    f"yang tercatat di Kecamatan *{kecamatan}*.\n\n"
                    f"💡 Coba tanyakan tanpa menyebut kecamatan untuk melihat "
                    f"semua lokasi *{olahraga}* di Tangsel."
                )
            )
            return []

        dispatcher.utter_message(
            text=(
                f"✅ Ditemukan *{len(rows)} prasarana {olahraga.title()}* "
                f"di Kecamatan *{kecamatan.title()}*:\n{SEPARATOR}"
            )
        )

        for i, r in enumerate(rows, 1):
            pesan = (
                f"*{i}. {r['nama_prasarana']}*\n"
                f"📍 {r['alamat']}\n"
                f"🏘️ Kec. {r['kecamatan']}\n"
                f"🗺️ {r['google_maps_link']}"
            )
            blok_harga = format_harga_block(r)
            if blok_harga:
                pesan += f"\n{SEPARATOR}\n{blok_harga}"
            dispatcher.utter_message(text=pesan)
            kirim_foto(dispatcher, r)

        log_chat(tracker, f"[{len(rows)} prasarana '{olahraga}' di '{kecamatan}' ditampilkan]")
        return []


class ActionDetailPrasarana(Action):
    """Menampilkan detail lengkap satu prasarana: alamat, harga tiap cabang, nomor pengelola, dan foto."""

    def name(self) -> Text:
        return "action_detail_prasarana"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        nama_prasarana: Optional[str] = get_entity_fresh(tracker, "nama_prasarana")

        if not nama_prasarana:
            dispatcher.utter_message(response="utter_ask_nama_prasarana")
            return []

        rows = query_db(
            """
            SELECT
                id, nama_prasarana, olahraga, alamat, kecamatan, google_maps_link, status,
                nomor_pengelola, harga_member_sesi_1, harga_member_sesi_2,
                harga_non_member_sesi_1, harga_non_member_sesi_2,
                link_gambar_1, link_gambar_2, link_gambar_3
            FROM prasarana_olahraga
            WHERE nama_prasarana ILIKE %s
            ORDER BY olahraga;
            """,
            (f"%{nama_prasarana}%",),
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(
                text=f"😔 Maaf, tidak ditemukan prasarana dengan nama *{nama_prasarana}*."
            )
            return []

        r0 = rows[0]
        daftar_olahraga = ", ".join(dict.fromkeys(r["olahraga"] for r in rows if r["olahraga"]))

        pesan = (
            f"🏟️ *{r0['nama_prasarana']}*\n"
            f"{SEPARATOR}\n"
            f"⚽ Cabang Olahraga : {daftar_olahraga}\n"
            f"📍 Alamat          : {r0['alamat']}\n"
            f"🏘️ Kecamatan       : {r0['kecamatan']}\n"
            f"📌 Status          : {r0['status']}\n"
            f"🗺️ Google Maps     : {r0['google_maps_link']}"
        )

        # Susun blok harga per cabang olahraga (kalau ada datanya)
        blok_harga_list = [format_harga_block(r) for r in rows]
        blok_harga_list = [b for b in blok_harga_list if b]

        if blok_harga_list:
            pesan += f"\n{SEPARATOR}\n" + f"\n{SEPARATOR}\n".join(blok_harga_list)

        dispatcher.utter_message(text=pesan)
        kirim_foto(dispatcher, r0)
        log_chat(tracker, f"[Detail prasarana '{r0['nama_prasarana']}' ditampilkan]")
        return []


class ActionListSemuaPrasarana(Action):
    """Menampilkan seluruh prasarana yang tercatat tanpa foto."""

    def name(self) -> Text:
        return "action_list_semua_prasarana"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        rows = query_db(
            """
            SELECT
                nama_prasarana,
                kecamatan,
                STRING_AGG(DISTINCT olahraga, ', ') AS daftar_olahraga
            FROM prasarana_olahraga
            WHERE status ILIKE 'aktif'
            GROUP BY nama_prasarana, kecamatan
            ORDER BY kecamatan, nama_prasarana;
            """
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(text="Belum ada data prasarana yang tercatat di database.")
            return []

        lines = [
            f"🏟️ *Daftar Prasarana Olahraga Kota Tangerang Selatan*",
            f"Total: *{len(rows)} prasarana aktif*\n{SEPARATOR}"
        ]
        kecamatan_sekarang = ""
        for r in rows:
            if r['kecamatan'] != kecamatan_sekarang:
                kecamatan_sekarang = r['kecamatan']
                lines.append(f"\n📍 *Kec. {kecamatan_sekarang}*")
            lines.append(f"  • {r['nama_prasarana']} — {r['daftar_olahraga']}")

        dispatcher.utter_message(text="\n".join(lines))
        log_chat(tracker, f"[Daftar {len(rows)} prasarana ditampilkan]")
        return []


class ActionListJenisOlahraga(Action):
    """Menampilkan seluruh jenis olahraga unik yang tercatat."""

    def name(self) -> Text:
        return "action_list_jenis_olahraga"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        rows = query_db(
            """
            SELECT DISTINCT olahraga
            FROM prasarana_olahraga
            WHERE status ILIKE 'aktif'
            ORDER BY olahraga;
            """
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(text="Belum ada data jenis olahraga yang tercatat.")
            return []

        daftar = "\n".join(f"  • {r['olahraga']}" for r in rows)
        dispatcher.utter_message(
            text=(
                f"⚽ *Cabang olahraga yang tersedia ({len(rows)} jenis):*\n"
                f"{SEPARATOR}\n"
                f"{daftar}\n\n"
                f"💡 Tanyakan lebih lanjut, contoh:\n"
                f"*'Lapangan futsal di mana?'*"
            )
        )
        log_chat(tracker, f"[Daftar {len(rows)} jenis olahraga ditampilkan]")
        return []


class ActionListKecamatan(Action):
    """Menampilkan seluruh kecamatan yang memiliki data prasarana."""

    def name(self) -> Text:
        return "action_list_kecamatan"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        rows = query_db(
            """
            SELECT DISTINCT kecamatan
            FROM prasarana_olahraga
            WHERE status ILIKE 'aktif'
            ORDER BY kecamatan;
            """
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(text="Belum ada data kecamatan yang tercatat.")
            return []

        daftar = "\n".join(f"  • {r['kecamatan']}" for r in rows)
        dispatcher.utter_message(
            text=(
                f"🏘️ *Kecamatan yang memiliki prasarana olahraga ({len(rows)} kecamatan):*\n"
                f"{SEPARATOR}\n"
                f"{daftar}\n\n"
                f"💡 Tanyakan lebih lanjut, contoh:\n"
                f"*'Prasarana olahraga di Pamulang?'*"
            )
        )
        log_chat(tracker, f"[Daftar {len(rows)} kecamatan ditampilkan]")
        return []

class ActionTarifPrasarana(Action):
    """Menampilkan tarif retribusi sebuah prasarana (khusus fasilitas yang punya data tarif, contoh: kolam renang)."""

    def name(self) -> Text:
        return "action_tarif_prasarana"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        nama_prasarana: Optional[str] = get_entity_fresh(tracker, "nama_prasarana")

        if not nama_prasarana:
            dispatcher.utter_message(response="utter_ask_nama_prasarana")
            return []

        prasarana_rows = query_db(
            """
            SELECT id, nama_prasarana
            FROM prasarana_olahraga
            WHERE nama_prasarana ILIKE %s
            LIMIT 1;
            """,
            (f"%{nama_prasarana}%",),
        )

        if prasarana_rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not prasarana_rows:
            dispatcher.utter_message(
                text=f"😔 Maaf, tidak ditemukan prasarana dengan nama *{nama_prasarana}*."
            )
            return []

        prasarana = prasarana_rows[0]

        tarif_rows = query_db(
            """
            SELECT jenis_pengunjung, kategori, tipe_hari, keterangan_tambahan, tarif, satuan
            FROM tarif_retribusi
            WHERE prasarana_id = %s
            ORDER BY jenis_pengunjung, id;
            """,
            (prasarana["id"],),
        )

        if tarif_rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not tarif_rows:
            dispatcher.utter_message(
                text=(
                    f"ℹ️ Untuk saat ini belum ada data tarif retribusi yang tercatat "
                    f"untuk *{prasarana['nama_prasarana']}*. Silakan hubungi pengelola "
                    f"langsung untuk info tarif terbaru."
                )
            )
            return []

        baris_pengunjung = []
        baris_rombongan = []
        for r in tarif_rows:
            harga = f"Rp{r['tarif']:,}".replace(",", ".")
            if r["jenis_pengunjung"] == "Pengunjung":
                hari = f" ({r['tipe_hari']})" if r["tipe_hari"] else ""
                baris_pengunjung.append(f"  • {r['kategori']}{hari}: {harga} / {r['satuan']}")
            else:
                ket = f" ({r['keterangan_tambahan']})" if r["keterangan_tambahan"] else ""
                baris_rombongan.append(f"  • {r['kategori']}{ket}: {harga} / {r['satuan']}")

        pesan = f"💰 *Tarif Retribusi {prasarana['nama_prasarana']}*\n{SEPARATOR}\n"
        if baris_pengunjung:
            pesan += "👤 Pengunjung:\n" + "\n".join(baris_pengunjung) + "\n"
        if baris_rombongan:
            pesan += "\n👥 Rombongan:\n" + "\n".join(baris_rombongan)

        dispatcher.utter_message(text=pesan.strip())
        log_chat(tracker, pesan.strip())
        return []


class ActionTarifSemuaKolam(Action):
    """Menampilkan tarif retribusi seluruh kolam renang sekaligus (dipicu tombol 'Daftar Tarif')."""

    def name(self) -> Text:
        return "action_tarif_semua_kolam"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        rows = query_db(
            """
            SELECT p.nama_prasarana, t.jenis_pengunjung, t.kategori, t.tipe_hari,
                   t.keterangan_tambahan, t.tarif, t.satuan
            FROM tarif_retribusi t
            JOIN prasarana_olahraga p ON p.id = t.prasarana_id
            WHERE p.olahraga = 'Renang'
            ORDER BY p.nama_prasarana, t.jenis_pengunjung, t.id;
            """
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(text="Belum ada data tarif kolam renang yang tercatat.")
            return []

        by_kolam: Dict[str, Dict[str, list]] = {}
        for r in rows:
            kolam = r["nama_prasarana"]
            by_kolam.setdefault(kolam, {"Pengunjung": [], "Rombongan": []})
            harga = f"Rp{r['tarif']:,}".replace(",", ".")
            if r["jenis_pengunjung"] == "Pengunjung":
                hari = f" ({r['tipe_hari']})" if r["tipe_hari"] else ""
                by_kolam[kolam]["Pengunjung"].append(f"  • {r['kategori']}{hari}: {harga} / {r['satuan']}")
            else:
                ket = f" ({r['keterangan_tambahan']})" if r["keterangan_tambahan"] else ""
                by_kolam[kolam]["Rombongan"].append(f"  • {r['kategori']}{ket}: {harga} / {r['satuan']}")

        pesan = f"💰 *Daftar Tarif Retribusi Kolam Renang*\n{SEPARATOR}\n"
        for kolam, kelompok in by_kolam.items():
            pesan += f"\n🏊 *{kolam}*\n"
            if kelompok["Pengunjung"]:
                pesan += "👤 Pengunjung:\n" + "\n".join(kelompok["Pengunjung"]) + "\n"
            if kelompok["Rombongan"]:
                pesan += "👥 Rombongan:\n" + "\n".join(kelompok["Rombongan"]) + "\n"

        dispatcher.utter_message(text=pesan.strip())
        log_chat(tracker, pesan.strip())
        return []
