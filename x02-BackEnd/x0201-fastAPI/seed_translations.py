#!/usr/bin/env python3
"""
Seed Translations Database
==========================
Reads the TypeScript dictionary file and imports all translations
into the SQLite database (translations.db).

Usage:
    python seed_translations.py

This script can be run multiple times safely — it uses UPSERT logic.
"""

import sqlite3
import os
import re
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
I18N_DIR = os.path.join(
    SCRIPT_DIR, "..", "..", "x01-FrontEnd", "x0101-xMixing_Nuxt",
    "app", "i18n"
)
DB_PATH = os.path.join(I18N_DIR, "translations.db")
DICTIONARY_PATH = os.path.join(I18N_DIR, "dictionary.ts")


def parse_dictionary(filepath: str) -> dict:
    """Parse the TypeScript dictionary file and extract translations."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    translations = {"en": {}, "th": {}}

    # Find each locale block
    for locale in ["en", "th"]:
        # Find the locale block: en: { ... } or th: { ... }
        # We'll use a simple line-by-line parser
        in_locale = False
        brace_depth = 0

        for line in content.split("\n"):
            stripped = line.strip()

            # Detect start of locale block
            if not in_locale:
                if re.match(rf"^\s*{locale}\s*:\s*\{{", line):
                    in_locale = True
                    brace_depth = 1
                    continue
            else:
                # Track braces
                brace_depth += stripped.count("{") - stripped.count("}")

                if brace_depth <= 0:
                    in_locale = False
                    continue

                # Parse key-value pairs like: 'common.save': 'Save',
                match = re.match(r"""^\s*'([^']+)'\s*:\s*['"](.*)['"],?\s*$""", line)
                if not match:
                    # Try double quotes
                    match = re.match(r"""^\s*"([^"]+)"\s*:\s*"(.*)",?\s*$""", line)
                if not match:
                    # Try mixed: 'key': "value"
                    match = re.match(r"""^\s*'([^']+)'\s*:\s*"(.*)",?\s*$""", line)
                if not match:
                    # Try: "key": 'value'
                    match = re.match(r"""^\s*"([^"]+)"\s*:\s*'(.*)',?\s*$""", line)

                if match:
                    key = match.group(1)
                    value = match.group(2)
                    # Unescape common sequences
                    value = value.replace("\\'", "'").replace('\\"', '"')
                    translations[locale][key] = value

    return translations


def seed_database(translations: dict):
    """Insert translations into SQLite database."""
    conn = sqlite3.connect(DB_PATH)
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

    total = 0
    for locale, pairs in translations.items():
        for key, value in pairs.items():
            conn.execute("""
                INSERT INTO translations (key, locale, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key, locale)
                DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """, (key, locale, value))
            total += 1

    conn.commit()

    # Stats
    en_count = conn.execute("SELECT COUNT(*) FROM translations WHERE locale='en'").fetchone()[0]
    th_count = conn.execute("SELECT COUNT(*) FROM translations WHERE locale='th'").fetchone()[0]
    conn.close()

    return total, en_count, th_count


def main():
    print("=" * 60)
    print("  Seed Translations Database")
    print("=" * 60)

    # Check dictionary file exists
    dict_path = os.path.abspath(DICTIONARY_PATH)
    if not os.path.exists(dict_path):
        print(f"❌ Dictionary file not found: {dict_path}")
        sys.exit(1)

    print(f"📖 Reading: {dict_path}")
    translations = parse_dictionary(dict_path)

    print(f"   EN keys found: {len(translations['en'])}")
    print(f"   TH keys found: {len(translations['th'])}")

    if not translations["en"] and not translations["th"]:
        print("❌ No translations parsed! Check the dictionary file format.")
        sys.exit(1)

    print(f"\n💾 Writing to: {os.path.abspath(DB_PATH)}")
    total, en_count, th_count = seed_database(translations)

    print(f"\n✅ Done!")
    print(f"   Total upserted: {total}")
    print(f"   EN in DB: {en_count}")
    print(f"   TH in DB: {th_count}")
    print(f"\n📂 Database file: {os.path.abspath(DB_PATH)}")
    print(f"   Open with: DB Browser for SQLite, DBeaver, or sqlite3 CLI")
    print("=" * 60)


if __name__ == "__main__":
    main()
