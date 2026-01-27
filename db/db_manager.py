"""
Database Manager for Price Scout.

This module provides SQLite database operations for storing and querying
product price history. Supports smart price tracking that only creates new
records when prices change, while updating timestamps for unchanged prices.

Classes:
    DatabaseManager: Main class for all database operations including
        product management, price tracking, and analytics queries.

Functions:
    init_database: Factory function to create a DatabaseManager instance.

Tables:
    products: Stores unique product identifiers (MPN).
    prices: Stores price records with vendor, price, and timestamp.

Example:
    >>> from db.db_manager import DatabaseManager
    >>> db = DatabaseManager()
    >>> db.add_price("BX8071512100F", "Scorptec", 245.00)
    >>> history = db.get_price_history("BX8071512100F", "Scorptec")
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("price-scout")

DB_PATH = Path(__file__).parent.parent / "app.db"
print(DB_PATH)


class DatabaseManager:
    """
    SQLite database manager for price tracking and analytics.

    Provides CRUD operations for products and prices, with intelligent
    price tracking that avoids duplicate records when prices remain unchanged.

    Attributes:
        db_path: Path to the SQLite database file.

    Example:
        >>> db = DatabaseManager()
        >>> db.add_price("BX8071512100F", "Scorptec", 245.00)
        >>> trends = db.get_price_trends_by_mpn("BX8071512100F")
    """

    def __init__(self, db_path: str = None):
        """
        Initialize database manager with optional custom path.

        Args:
            db_path: Optional path to SQLite database file.
                     Defaults to app.db in project root.
        """
        self.db_path = db_path or str(DB_PATH)
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def _create_tables(self):
        """Create the products and prices tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mpn TEXT NOT NULL UNIQUE
                )
            """)

            # Create prices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    vendor_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    scraped_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                )
            """)

            # Create index on product_id for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prices_product_id
                ON prices (product_id)
            """)

            # Create index on scraped_at for time-based queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prices_scraped_at
                ON prices (scraped_at)
            """)

            conn.commit()
            logger.info("Database tables created successfully")

    # Product operations
    def add_product(self, mpn: str) -> Optional[int]:
        """
        Add a new product with MPN to the database.
        Returns the product ID if successful, None if product already exists.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (mpn) VALUES (?)", (mpn,))
                conn.commit()
                product_id = cursor.lastrowid
                logger.info(f"Added product: {mpn} (ID: {product_id})")
                return product_id
        except sqlite3.IntegrityError:
            logger.warning(f"Product with MPN '{mpn}' already exists")
            return None

    def get_product_by_mpn(self, mpn: str) -> Optional[Dict]:
        """Get product by MPN. Returns dict with id and mpn, or None if not found."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, mpn FROM products WHERE mpn = ?", (mpn,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get product by ID. Returns dict with id and mpn, or None if not found."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, mpn FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_products(self) -> List[Dict]:
        """Get all products from the database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, mpn FROM products ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]

    def get_or_create_product(self, mpn: str) -> int:
        """
        Get existing product ID or create new product if it doesn't exist.
        Always returns a product ID.
        """
        product = self.get_product_by_mpn(mpn)
        if product:
            return product['id']
        else:
            return self.add_product(mpn)

    # Price operations
    def add_price(self, mpn: str, vendor_name: str, price: float,
                  scraped_at: datetime = None) -> Optional[int]:
        """
        Add a price entry for a product. Creates product if it doesn't exist.
        Returns the price record ID if successful.
        """
        if scraped_at is None:
            scraped_at = datetime.now()

        product_id = self.get_or_create_product(mpn)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO prices (product_id, vendor_name, price, scraped_at)
                    VALUES (?, ?, ?, ?)
                """, (product_id, vendor_name, price, scraped_at.isoformat()))
                conn.commit()
                price_id = cursor.lastrowid
                logger.info(f"Added price: {mpn} - {vendor_name} - ${price}")
                return price_id
        except sqlite3.Error as e:
            logger.error(f"Error adding price: {e}")
            return None

    def update_price_timestamp(self, mpn: str, vendor_name: str,
                               scraped_at: datetime = None) -> bool:
        """
        Update the scraped_at timestamp of the most recent price record
        for a specific product and vendor.
        Returns True if successful, False otherwise.
        """
        if scraped_at is None:
            scraped_at = datetime.now()

        product = self.get_product_by_mpn(mpn)
        if not product:
            logger.warning(f"Cannot update timestamp: Product '{mpn}' not found")
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE prices
                    SET scraped_at = ?
                    WHERE id = (
                        SELECT id FROM prices
                        WHERE product_id = ? AND vendor_name = ?
                        ORDER BY scraped_at DESC
                        LIMIT 1
                    )
                """, (scraped_at.isoformat(), product['id'], vendor_name))
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Updated timestamp: {mpn} - {vendor_name}")
                    return True
                else:
                    logger.warning(f"No price record found to update: {mpn} - {vendor_name}")
                    return False
        except sqlite3.Error as e:
            logger.error(f"Error updating timestamp: {e}")
            return False

    def get_prices_by_mpn(self, mpn: str) -> List[Dict]:
        """Get all price records for a specific MPN"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.product_id, prod.mpn, p.vendor_name,
                       p.price, p.scraped_at
                FROM prices p
                JOIN products prod ON p.product_id = prod.id
                WHERE prod.mpn = ?
                ORDER BY p.scraped_at DESC
            """, (mpn,))
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_prices_by_mpn(self, mpn: str) -> List[Dict]:
        """Get the most recent price from each vendor for a specific MPN"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.product_id, prod.mpn, p.vendor_name,
                       p.price, p.scraped_at
                FROM prices p
                JOIN products prod ON p.product_id = prod.id
                WHERE prod.mpn = ?
                AND p.id IN (
                    SELECT MAX(id)
                    FROM prices
                    WHERE product_id = p.product_id
                    GROUP BY vendor_name
                )
                ORDER BY p.price ASC
            """, (mpn,))
            return [dict(row) for row in cursor.fetchall()]

    def get_prices_by_vendor(self, vendor_name: str) -> List[Dict]:
        """Get all price records for a specific vendor"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.product_id, prod.mpn, p.vendor_name,
                       p.price, p.scraped_at
                FROM prices p
                JOIN products prod ON p.product_id = prod.id
                WHERE p.vendor_name = ?
                ORDER BY p.scraped_at DESC
            """, (vendor_name,))
            return [dict(row) for row in cursor.fetchall()]

    def get_price_history(self, mpn: str, vendor_name: str) -> List[Dict]:
        """Get price history for a specific product from a specific vendor"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.product_id, prod.mpn, p.vendor_name,
                       p.price, p.scraped_at
                FROM prices p
                JOIN products prod ON p.product_id = prod.id
                WHERE prod.mpn = ? AND p.vendor_name = ?
                ORDER BY p.scraped_at DESC
            """, (mpn, vendor_name))
            return [dict(row) for row in cursor.fetchall()]

    def delete_old_prices(self, days: int = 30) -> int:
        """Delete price records older than specified days. Returns count of deleted records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM prices
                WHERE scraped_at < datetime('now', '-' || ? || ' days')
            """, (days,))
            conn.commit()
            deleted_count = cursor.rowcount
            logger.info(f"Deleted {deleted_count} old price records")
            return deleted_count

    def clear_database(self) -> Dict[str, int]:
        """
        Clear all data from the database (both prices and products tables).
        Returns a dictionary with counts of deleted records.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count records before deletion
            cursor.execute("SELECT COUNT(*) FROM prices")
            prices_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM products")
            products_count = cursor.fetchone()[0]

            # Delete all prices first (due to foreign key constraint)
            cursor.execute("DELETE FROM prices")

            # Delete all products
            cursor.execute("DELETE FROM products")

            conn.commit()

            logger.info(f"Cleared database: {prices_count} prices, {products_count} products deleted")

            return {
                'prices_deleted': prices_count,
                'products_deleted': products_count
            }

    # Analytics operations
    def get_all_mpns_with_prices(self) -> List[str]:
        """Get all MPNs that have price data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT prod.mpn
                FROM products prod
                JOIN prices p ON prod.id = p.product_id
                ORDER BY prod.mpn
            """)
            return [row[0] for row in cursor.fetchall()]

    def get_price_trends_by_mpn(self, mpn: str) -> Dict:
        """
        Get price trends for an MPN across all vendors.
        Returns a dict with vendor_name as key and list of {date, price} as value.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.vendor_name, p.price, p.scraped_at
                FROM prices p
                JOIN products prod ON p.product_id = prod.id
                WHERE prod.mpn = ?
                ORDER BY p.vendor_name, p.scraped_at
            """, (mpn,))

            rows = cursor.fetchall()
            trends = {}
            for row in rows:
                vendor = row['vendor_name']
                if vendor not in trends:
                    trends[vendor] = []
                trends[vendor].append({
                    'date': row['scraped_at'],
                    'price': row['price']
                })
            return trends

    def get_average_prices_by_mpn(self, mpn: str) -> Dict:
        """
        Get average prices for an MPN.
        Returns dict with overall_avg and per_vendor_avg.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Overall average
            cursor.execute("""
                SELECT AVG(p.price) as avg_price
                FROM prices p
                JOIN products prod ON p.product_id = prod.id
                WHERE prod.mpn = ?
            """, (mpn,))
            overall_avg = cursor.fetchone()['avg_price']

            # Per vendor average
            cursor.execute("""
                SELECT p.vendor_name, AVG(p.price) as avg_price, COUNT(*) as count
                FROM prices p
                JOIN products prod ON p.product_id = prod.id
                WHERE prod.mpn = ?
                GROUP BY p.vendor_name
                ORDER BY avg_price
            """, (mpn,))

            vendor_avgs = [dict(row) for row in cursor.fetchall()]

            return {
                'overall_avg': overall_avg,
                'vendor_avgs': vendor_avgs
            }


def init_database(db_path: str = None) -> DatabaseManager:
    """Initialize and return a DatabaseManager instance"""
    return DatabaseManager(db_path)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Initialize database
    db = init_database()
    db.clear_database()
      
    # # Add some sample data
    # print("Adding sample products and prices...")
    # db.add_price("MPN-12345", "Vendor A", 99.99)
    # db.add_price("MPN-12345", "Vendor B", 95.50)
    # db.add_price("MPN-67890", "Vendor A", 149.99)

    # # Query data
    # print("\nAll products:")
    # products = db.get_all_products()
    # for product in products:
    #     print(f"  ID: {product['id']}, MPN: {product['mpn']}")

    # print("\nLatest prices for MPN-12345:")
    # prices = db.get_latest_prices_by_mpn("MPN-12345")
    # for price in prices:
    #     print(f"  {price['vendor_name']}: ${price['price']} (at {price['scraped_at']})")

    # print("\nPrice history for MPN-12345 from Vendor A:")
    # history = db.get_price_history("MPN-12345", "Vendor A")
    # for record in history:
    #     print(f"  ${record['price']} at {record['scraped_at']}")
