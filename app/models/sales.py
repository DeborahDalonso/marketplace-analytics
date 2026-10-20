import sqlite3
from typing import Any

COLUMNS = ('order_id', 'product_id', 'seller_id', 'buyer_id', 'quantity', 'price_cents', 'paid_at')


class SaleModel:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def insert_many(self, rows: list[dict[str, Any]]) -> int:
        # OR IGNORE segura a repetição do mesmo item do pedido vinda em eventos distintos
        cursor = self.conn.executemany(
            'INSERT OR IGNORE INTO sales (order_id, product_id, seller_id, buyer_id, quantity, price_cents, paid_at) '
            'VALUES (:order_id, :product_id, :seller_id, :buyer_id, :quantity, :price_cents, :paid_at)',
            rows,
        )
        return cursor.rowcount

    def fetch(self, from_iso: str, to_iso: str, seller_id: str | None = None) -> list[dict[str, Any]]:
        sql = 'SELECT ' + ', '.join(COLUMNS) + ' FROM sales WHERE paid_at >= ? AND paid_at < ?'
        params: list[Any] = [from_iso, to_iso]
        if seller_id is not None:
            sql += ' AND seller_id = ?'
            params.append(seller_id)
        return [dict(row) for row in self.conn.execute(sql + ' ORDER BY paid_at', params)]
