"""
Translations Router
===================
Serves i18n translations from a local SQLite database.
The SQLite file (translations.db) can be edited with any SQLite tool
(e.g. DB Browser for SQLite, DBeaver, or command-line sqlite3).

Endpoints:
  GET  /translations/              → all translations (both locales)
  GET  /translations/{locale}      → all key-value pairs for a locale
  PUT  /translations/{locale}/{key} → update a single translation
  POST /translations/bulk          → bulk upsert translations
"""

import sqlite3
import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Translations"])

# SQLite database path — sits next to this file for portability
DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DB_DIR, "translations.db")


def get_conn():
    """Get a connection to the translations SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the translations table if it doesn't exist."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            locale TEXT NOT NULL DEFAULT 'en',
            value TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(key, locale)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_translations_locale
        ON translations(locale)
    """)
    conn.commit()
    conn.close()
    logger.info(f"✅ Translations DB ready at: {DB_PATH}")


# Initialize on module import
init_db()


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/translations/")
def get_all_translations():
    """Get all translations grouped by locale."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT key, locale, value FROM translations ORDER BY locale, key"
    ).fetchall()
    conn.close()

    result: dict = {}
    for row in rows:
        locale = row["locale"]
        if locale not in result:
            result[locale] = {}
        result[locale][row["key"]] = row["value"]

    return result


@router.get("/translations/stats")
def get_translation_stats():
    """Get statistics about translations."""
    conn = get_conn()

    total = conn.execute("SELECT COUNT(*) as cnt FROM translations").fetchone()["cnt"]
    en_count = conn.execute("SELECT COUNT(*) as cnt FROM translations WHERE locale='en'").fetchone()["cnt"]
    th_count = conn.execute("SELECT COUNT(*) as cnt FROM translations WHERE locale='th'").fetchone()["cnt"]

    # Find keys missing in Thai
    missing_th = conn.execute("""
        SELECT t1.key FROM translations t1
        WHERE t1.locale = 'en'
        AND NOT EXISTS (
            SELECT 1 FROM translations t2
            WHERE t2.key = t1.key AND t2.locale = 'th'
        )
    """).fetchall()

    conn.close()

    return {
        "total_entries": total,
        "en_count": en_count,
        "th_count": th_count,
        "missing_in_th": [r["key"] for r in missing_th],
    }


class BulkTranslation(BaseModel):
    key: str
    locale: str
    value: str


@router.post("/translations/bulk")
def bulk_upsert_translations(items: list[BulkTranslation]):
    """Bulk upsert translations. Used by the seed script."""
    conn = get_conn()
    inserted = 0
    for item in items:
        conn.execute("""
            INSERT INTO translations (key, locale, value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key, locale)
            DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """, (item.key, item.locale, item.value))
        inserted += 1
    conn.commit()
    conn.close()

    return {"status": "ok", "upserted": inserted}


@router.get("/translations/{locale}")
def get_translations_by_locale(locale: str):
    """Get all translations for a specific locale as a flat key-value object."""
    if locale not in ("en", "th"):
        raise HTTPException(status_code=400, detail="Locale must be 'en' or 'th'")

    conn = get_conn()
    rows = conn.execute(
        "SELECT key, value FROM translations WHERE locale = ? ORDER BY key",
        (locale,)
    ).fetchall()
    conn.close()

    return {row["key"]: row["value"] for row in rows}


class TranslationUpdate(BaseModel):
    value: str


@router.put("/translations/{locale}/{key:path}")
def update_translation(locale: str, key: str, body: TranslationUpdate):
    """Update a single translation value."""
    if locale not in ("en", "th"):
        raise HTTPException(status_code=400, detail="Locale must be 'en' or 'th'")

    conn = get_conn()

    # Upsert: insert or update
    conn.execute("""
        INSERT INTO translations (key, locale, value, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key, locale)
        DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, locale, body.value))
    conn.commit()
    conn.close()

    return {"status": "ok", "key": key, "locale": locale, "value": body.value}

