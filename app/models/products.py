import sqlite3
from typing import Any

COLUMNS = ('product_id', 'seller_id', 'category_id', 'name', 'price_cents', 'created_at')


class ProductModel:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, product: dict[str, Any]) -> None:
        # created_at só entra na primeira vez; update mantém a data original
        self.conn.execute(
            'INSERT INTO products (product_id, seller_id, category_id, name, price_cents, created_at) '
            'VALUES (:product_id, :seller_id, :category_id, :name, :price_cents, :created_at) '
            'ON CONFLICT (product_id) DO UPDATE SET '
            'seller_id = excluded.seller_id, category_id = excluded.category_id, '
            'name = excluded.name, price_cents = excluded.price_cents',
            product,
        )

    def find(self, product_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            'SELECT ' + ', '.join(COLUMNS) + ' FROM products WHERE product_id = ?', (product_id,)
        ).fetchone()
        return dict(row) if row else None

    def fetch(self, seller_id: str | None = None) -> list[dict[str, Any]]:
        sql = 'SELECT ' + ', '.join(COLUMNS) + ' FROM products'
        params: list[Any] = []
        if seller_id is not None:
            sql += ' WHERE seller_id = ?'
            params.append(seller_id)
        return [dict(row) for row in self.conn.execute(sql, params)]
