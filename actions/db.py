"""
Modul koneksi database PostgreSQL untuk custom actions Rasa.
Konfigurasi diambil dari environment variable (lihat file .env / .env.example),
agar kredensial database tidak hardcode di kode.
"""

import os
import logging
from typing import Optional, List, Dict, Any, Tuple

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"Environment variable '{key}' belum diset. "
            f"Cek file .env kamu (lihat .env.example sebagai referensi)."
        )
    return value


def _get_db_config():
    return {
        "host": _require_env("DB_HOST"),
        "port": os.environ.get("DB_PORT", "5432"),
        "dbname": os.environ.get("DB_NAME", "postgres"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": _require_env("DB_PASSWORD"),
    }


def get_connection():
    """Membuka koneksi baru ke database PostgreSQL, konfigurasi dari environment variable."""
    return psycopg2.connect(**_get_db_config())


def query_db(sql: str, params: Optional[Tuple] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Menjalankan query SELECT dan mengembalikan list of dict.
    Mengembalikan None jika terjadi error koneksi/query (bukan list kosong,
    supaya action bisa membedakan 'gagal query' vs 'data tidak ditemukan').
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Database error saat menjalankan query: {e}")
        return None
    finally:
        if conn is not None:
            conn.close()