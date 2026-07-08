"""
Script untuk import/update data prasarana olahraga dari file Excel ke database
Supabase (PostgreSQL). Bisa dijalankan berulang kali -- data yang sudah ada
(dicek dari kombinasi nama_prasarana + olahraga) akan di-UPDATE, bukan
di-duplikat.

Cara pakai:
    python scripts/import_excel_to_db.py path/ke/Data_Prasarana.xlsx

Excel WAJIB punya kolom (header di baris manapun, urutan bebas):
    Nama Prasarana | Olahraga | Alamat | Kecamatan | Google maps link |
    Status | Link Gambar 1 | Link gambar 2 | Link Gambar 3

Kredensial database diambil dari .env (lihat .env.example).
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from actions.db import get_connection  # noqa: E402

COLUMN_MAP = {
    "nama prasarana": "nama_prasarana",
    "olahraga": "olahraga",
    "alamat": "alamat",
    "kecamatan": "kecamatan",
    "google maps link": "google_maps_link",
    "status": "status",
    "link gambar 1": "link_gambar_1",
    "link gamabar 1": "link_gambar_1",  # antisipasi typo umum
    "link gambar 2": "link_gambar_2",
    "link gambar 3": "link_gambar_3",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS prasarana_olahraga (
    id SERIAL PRIMARY KEY,
    nama_prasarana TEXT NOT NULL,
    olahraga TEXT NOT NULL,
    alamat TEXT,
    kecamatan TEXT NOT NULL,
    google_maps_link TEXT,
    status TEXT DEFAULT 'Aktif',
    link_gambar_1 TEXT,
    link_gambar_2 TEXT,
    link_gambar_3 TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (nama_prasarana, olahraga)
);
"""

UPSERT_SQL = """
INSERT INTO prasarana_olahraga
    (nama_prasarana, olahraga, alamat, kecamatan, google_maps_link, status,
     link_gambar_1, link_gambar_2, link_gambar_3)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (nama_prasarana, olahraga) DO UPDATE SET
    alamat = EXCLUDED.alamat,
    kecamatan = EXCLUDED.kecamatan,
    google_maps_link = EXCLUDED.google_maps_link,
    status = EXCLUDED.status,
    link_gambar_1 = EXCLUDED.link_gambar_1,
    link_gambar_2 = EXCLUDED.link_gambar_2,
    link_gambar_3 = EXCLUDED.link_gambar_3;
"""


def find_header_row(path: str, sheet_name) -> int:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=15)
    for i, row in raw.iterrows():
        cells = [str(c).strip().lower() for c in row if pd.notna(c)]
        if "nama prasarana" in cells:
            return i
    raise ValueError("Baris header ('Nama Prasarana', dst) tidak ditemukan di 15 baris pertama.")


def load_excel(path: str) -> pd.DataFrame:
    sheet_name = 0
    header_row = find_header_row(path, sheet_name)
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    df = df.dropna(axis=1, how="all")
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in COLUMN_MAP:
            rename[col] = COLUMN_MAP[key]
    df = df.rename(columns=rename)

    required = {"nama_prasarana", "olahraga", "kecamatan"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan di Excel: {missing}")

    for col in ["alamat", "google_maps_link", "status", "link_gambar_1", "link_gambar_2", "link_gambar_3"]:
        if col not in df.columns:
            df[col] = None

    df = df.dropna(subset=["nama_prasarana", "olahraga", "kecamatan"])
    return df


def main(path: str):
    df = load_excel(path)
    print(f"Ditemukan {len(df)} baris data di '{path}'.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            for _, r in df.iterrows():
                cur.execute(UPSERT_SQL, (
                    r["nama_prasarana"], r["olahraga"], r.get("alamat"),
                    r["kecamatan"], r.get("google_maps_link"), r.get("status") or "Aktif",
                    r.get("link_gambar_1"), r.get("link_gambar_2"), r.get("link_gambar_3"),
                ))
        conn.commit()
        print(f"Berhasil import/update {len(df)} baris ke tabel 'prasarana_olahraga'.")
    except Exception as e:
        conn.rollback()
        print(f"Gagal import: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Cara pakai: python scripts/import_excel_to_db.py path/ke/file.xlsx")
        sys.exit(1)
    main(sys.argv[1])
