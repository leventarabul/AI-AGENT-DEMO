"""Run pending SQL migrations on startup.

Tracks executed migrations in a `schema_migrations` table.
Migration files live in the `migrations/` directory next to
this script and are executed in alphabetical order.
"""

import os
import glob
import logging
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "campaign_demo"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "admin123"),
}

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "migrations"
)


def ensure_migrations_table(conn):
    """Create schema_migrations table if it does not exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def get_applied_migrations(conn):
    """Return set of already-applied migration filenames."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT filename FROM schema_migrations"
        )
        return {row[0] for row in cur.fetchall()}


def apply_migration(conn, filepath, filename):
    """Execute a single migration file inside a transaction."""
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()

    if not sql.strip():
        logger.info(f"  Skipping empty migration: {filename}")
        return

    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            "INSERT INTO schema_migrations (filename) "
            "VALUES (%s)",
            (filename,),
        )
    conn.commit()
    logger.info(f"  ✅ Applied: {filename}")


def run_migrations():
    """Discover and apply pending migrations."""
    if not os.path.isdir(MIGRATIONS_DIR):
        logger.info("No migrations directory found; skipping.")
        return

    migration_files = sorted(
        glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql"))
    )
    if not migration_files:
        logger.info("No migration files found.")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        ensure_migrations_table(conn)
        applied = get_applied_migrations(conn)

        pending = [
            f for f in migration_files
            if os.path.basename(f) not in applied
        ]

        if not pending:
            logger.info("All migrations already applied.")
            return

        logger.info(
            f"Applying {len(pending)} pending migration(s)..."
        )
        for filepath in pending:
            filename = os.path.basename(filepath)
            try:
                apply_migration(conn, filepath, filename)
            except Exception as e:
                conn.rollback()
                logger.error(
                    f"  ❌ Migration failed: {filename}: {e}"
                )
                raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migrations()
