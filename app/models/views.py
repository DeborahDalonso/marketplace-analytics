import sqlite3
from typing import Any


class ProductViewModel:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert(self, product_id: str, user_id: str | None, viewed_at: str) -> None:
        self.conn.execute(
            'INSERT INTO product_views (product_id, user_id, viewed_at) VALUES (?, ?, ?)',
            (product_id, user_id, viewed_at),
        )

    def fetch(self, from_iso: str, to_iso: str, seller_id: str | None = None) -> list[dict[str, Any]]:
        """Visualizações no período; com seller_id só as de produtos conhecidos daquele vendedor."""
        sql = (
            'SELECT v.product_id, v.user_id, v.viewed_at FROM product_views v '
            'LEFT JOIN products p ON p.product_id = v.product_id '
            'WHERE v.viewed_at >= ? AND v.viewed_at < ?'
        )
        params: list[Any] = [from_iso, to_iso]
        if seller_id is not None:
            sql += ' AND p.seller_id = ?'
            params.append(seller_id)
        return [dict(row) for row in self.conn.execute(sql + ' ORDER BY v.viewed_at', params)]
