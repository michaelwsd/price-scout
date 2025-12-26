# database.py
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger("price-scout")

DB_NAME = "prices.db"


def init_db():
    """initialize database structure"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # create price record table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS price_history
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       mpn
                       TEXT
                       NOT
                       NULL,
                       vendor
                       TEXT
                       NOT
                       NULL,
                       price
                       REAL,
                       currency
                       TEXT,
                       url
                       TEXT,
                       found
                       BOOLEAN,
                       scraped_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized.")


def save_result(result):
    """save single PriceResult object to db"""
    # PriceResult from models.py
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
                   INSERT INTO price_history (mpn, vendor, price, currency, url, found, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ''', (
                       result.mpn,
                       result.vendor_id,
                       result.price,
                       result.currency,
                       result.url,
                       result.found,
                       datetime.now()
                   ))

    conn.commit()
    conn.close()


def get_history_by_mpn(mpn: str) -> List[Dict]:
    """get every record of certain mpn"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # make result accessible by column name
    cursor = conn.cursor()

    cursor.execute('''
                   SELECT *
                   FROM price_history
                   WHERE mpn = ? AND found = 1
                   ORDER BY price ASC
                   ''', (mpn,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]