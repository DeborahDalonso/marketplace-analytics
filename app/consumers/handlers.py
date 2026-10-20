import logging
import sqlite3
from collections.abc import Callable
from typing import Any

from app.db import parse_iso, utc_iso
from app.models.processed_events import ProcessedEventModel
from app.models.products import ProductModel
from app.models.sales import SaleModel
from app.models.views import ProductViewModel

logger = logging.getLogger(__name__)

TOPICS = ('order.paid', 'product.created', 'product.updated', 'product.viewed')


class EventHandlers:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.processed = ProcessedEventModel(conn)
        self.sales = SaleModel(conn)
        self.products = ProductModel(conn)
        self.views = ProductViewModel(conn)
        self._handlers: dict[str, Callable[[dict[str, Any]], None]] = {
            'order.paid': self._order_paid,
            'product.created': self._product_upsert,
            'product.updated': self._product_upsert,
            'product.viewed': self._product_viewed,
        }

    def handle(self, event: dict[str, Any]) -> bool:
        """Processa um envelope de evento. Devolve False quando ignorado (repetido ou tipo desconhecido)."""
        event_type = event.get('type')
        handler = self._handlers.get(event_type)
        if handler is None:
            logger.warning('Evento de tipo desconhecido ignorado: %s', event_type)
            return False
        # Marca e grava na mesma transação: se a gravação falhar, a marca também volta
        with self.conn:
            if not self.processed.mark(event['eventId'], event_type):
                logger.info('Evento repetido ignorado: %s (%s)', event['eventId'], event_type)
                return False
            handler(event)
        logger.debug('Evento processado: %s (%s)', event['eventId'], event_type)
        return True

    def _order_paid(self, event: dict[str, Any]) -> None:
        data = event['data']
        paid_at = _occurred_at(event)
        rows = [
            {
                'order_id': data['orderId'],
                'product_id': item['productId'],
                'seller_id': item['sellerId'],
                'buyer_id': data['buyerId'],
                'quantity': item['quantity'],
                'price_cents': item['priceCents'],
                'paid_at': paid_at,
            }
            for item in data['items']
        ]
        self.sales.insert_many(rows)

    def _product_upsert(self, event: dict[str, Any]) -> None:
        data = event['data']
        self.products.upsert(
            {
                'product_id': data['productId'],
                'seller_id': data['sellerId'],
                'category_id': data.get('categoryId'),
                'name': data['name'],
                'price_cents': data['priceCents'],
                'created_at': _occurred_at(event),
            }
        )

    def _product_viewed(self, event: dict[str, Any]) -> None:
        data = event['data']
        self.views.insert(data['productId'], data.get('userId'), _occurred_at(event))


def _occurred_at(event: dict[str, Any]) -> str:
    return utc_iso(parse_iso(event['occurredAt']))
