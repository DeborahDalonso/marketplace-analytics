import sqlite3
from datetime import UTC, datetime
from pathlib import Path

# Datas guardadas como texto ISO em UTC sem offset, para a comparação em SQL
# funcionar como string
ISO_FORMAT = '%Y-%m-%dT%H:%M:%S'

MIGRATIONS: list[tuple[str, tuple[str, ...]]] = [
    (
        '001_processed_events',
        (
            """CREATE TABLE processed_events (
                event_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                processed_at TEXT NOT NULL
            )""",
        ),
    ),
    (
        '002_sales',
        (
            """CREATE TABLE sales (
                id INTEGER PRIMARY KEY,
                order_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price_cents INTEGER NOT NULL,
                paid_at TEXT NOT NULL,
                UNIQUE (order_id, product_id)
            )""",
            'CREATE INDEX idx_sales_seller_paid ON sales (seller_id, paid_at)',
            'CREATE INDEX idx_sales_paid ON sales (paid_at)',
        ),
    ),
    (
        '003_products',
        (
            """CREATE TABLE products (
                product_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                category_id TEXT,
                name TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )""",
            'CREATE INDEX idx_products_seller ON products (seller_id)',
        ),
    ),
    (
        '004_product_views',
        (
            """CREATE TABLE product_views (
                id INTEGER PRIMARY KEY,
                product_id TEXT NOT NULL,
                user_id TEXT,
                viewed_at TEXT NOT NULL
            )""",
            'CREATE INDEX idx_product_views_product_viewed ON product_views (product_id, viewed_at)',
        ),
    ),
]


def connect(db_path: str) -> sqlite3.Connection:
    if db_path != ':memory:':
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    if db_path != ':memory:':
        # WAL deixa as rotas lerem enquanto o consumer grava
        conn.execute('PRAGMA journal_mode = WAL')
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """Aplica as migrations pendentes em ordem e devolve quantas rodaram."""
    conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)')
    applied = {row['name'] for row in conn.execute('SELECT name FROM schema_migrations')}
    count = 0
    for name, statements in MIGRATIONS:
        if name in applied:
            continue
        with conn:
            for sql in statements:
                conn.execute(sql)
            conn.execute('INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)', (name, utc_iso(now_utc())))
        count += 1
    return count


def now_utc() -> datetime:
    return datetime.now(UTC)


def utc_iso(value: datetime) -> str:
    """Normaliza qualquer datetime para o formato de texto usado nas tabelas."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC)
    return value.strftime(ISO_FORMAT)


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))
