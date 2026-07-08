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

from .db import query_db

ERROR_DB = (
    "⚠️ Maaf, saat ini saya tidak bisa mengakses data prasarana karena ada "
    "gangguan koneksi ke database. Silakan coba lagi beberapa saat lagi."
)

SEPARATOR = "─────────────────────"


def kirim_foto(dispatcher: CollectingDispatcher, row: Dict[str, Any]) -> None:
    """
    Mengirim foto 1, 2, dan 3 dari satu baris data prasarana ke chat widget.
    Link Cloudinary sudah berupa direct URL — langsung dipakai tanpa konversi.
    """
    for kolom in ("link_gambar_1", "link_gambar_2", "link_gambar_3"):
        url = row.get(kolom)
        if url:
            dispatcher.utter_message(image=url)


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
        olahraga: Optional[str] = tracker.get_slot("olahraga")

        if not olahraga:
            dispatcher.utter_message(response="utter_ask_olahraga")
            return []

        rows = query_db(
            """
            SELECT nama_prasarana, alamat, kecamatan, google_maps_link,
                   link_gambar_1, link_gambar_2, link_gambar_3
            FROM prasarana_olahraga
            WHERE olahraga ILIKE %s AND status ILIKE 'aktif'
            ORDER BY kecamatan, nama_prasarana;
            """,
            (f"%{olahraga}%",),
        )

        if rows is None:
            dispatcher.utter_message(text=ERROR_DB)
            return []

        if not rows:
            dispatcher.utter_message(
                text=f"😔 Maaf, belum ada prasarana untuk olahraga *{olahraga}* yang tercatat."
            )
            return []

        dispatcher.utter_message(
            text=(
                f"🔍 Ditemukan *{len(rows)} prasarana* untuk olahraga *{olahraga.title()}* "
                f"di Kota Tangerang Selatan:\n{SEPARATOR}"
            )
        )

        for i, r in enumerate(rows, 1):
            dispatcher.utter_message(
                text=(
                    f"*{i}. {r['nama_prasarana']}*\n"
                    f"📍 {r['alamat']}\n"
                    f"🏘️ Kec. {r['kecamatan']}\n"
                    f"🗺️ {r['google_maps_link']}"
                )
            )
            kirim_foto(dispatcher, r)

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
        kecamatan: Optional[str] = tracker.get_slot("kecamatan")

        if not kecamatan:
            dispatcher.utter_message(response="utter_ask_kecamatan")
            return []

        rows = query_db(
            """
            SELECT nama_prasarana, olahraga, alamat, google_maps_link,
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
            dispatcher.utter_message(
                text=(
                    f"*{i}. {r['nama_prasarana']}*\n"
                    f"⚽ {r['olahraga']}\n"
                    f"📍 {r['alamat']}\n"
                    f"🗺️ {r['google_maps_link']}"
                )
            )
            kirim_foto(dispatcher, r)

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
        olahraga: Optional[str] = tracker.get_slot("olahraga")
        kecamatan: Optional[str] = tracker.get_slot("kecamatan")

        if not olahraga:
            dispatcher.utter_message(response="utter_ask_olahraga")
            return []

        if not kecamatan:
            dispatcher.utter_message(response="utter_ask_kecamatan")
            return []

        rows = query_db(
            """
            SELECT nama_prasarana, alamat, kecamatan, google_maps_link,
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
            dispatcher.utter_message(
                text=(
                    f"*{i}. {r['nama_prasarana']}*\n"
                    f"📍 {r['alamat']}\n"
                    f"🏘️ Kec. {r['kecamatan']}\n"
                    f"🗺️ {r['google_maps_link']}"
                )
            )
            kirim_foto(dispatcher, r)

        return []


class ActionDetailPrasarana(Action):
    """Menampilkan detail lengkap satu prasarana beserta semua fotonya."""

    def name(self) -> Text:
        return "action_detail_prasarana"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        nama_prasarana: Optional[str] = tracker.get_slot("nama_prasarana")

        if not nama_prasarana:
            dispatcher.utter_message(response="utter_ask_nama_prasarana")
            return []

        rows = query_db(
            """
            SELECT
                nama_prasarana,
                alamat,
                kecamatan,
                google_maps_link,
                status,
                STRING_AGG(DISTINCT olahraga, ', ') AS daftar_olahraga,
                MAX(link_gambar_1) AS link_gambar_1,
                MAX(link_gambar_2) AS link_gambar_2,
                MAX(link_gambar_3) AS link_gambar_3
            FROM prasarana_olahraga
            WHERE nama_prasarana ILIKE %s
            GROUP BY nama_prasarana, alamat, kecamatan, google_maps_link, status
            LIMIT 1;
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

        r = rows[0]
        dispatcher.utter_message(
            text=(
                f"🏟️ *{r['nama_prasarana']}*\n"
                f"{SEPARATOR}\n"
                f"⚽ Cabang Olahraga : {r['daftar_olahraga']}\n"
                f"📍 Alamat          : {r['alamat']}\n"
                f"🏘️ Kecamatan       : {r['kecamatan']}\n"
                f"📌 Status          : {r['status']}\n"
                f"🗺️ Google Maps     : {r['google_maps_link']}"
            )
        )
        kirim_foto(dispatcher, r)
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
        return []