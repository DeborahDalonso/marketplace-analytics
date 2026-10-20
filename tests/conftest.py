import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.consumers.handlers import EventHandlers
from app.db import connect, migrate
from app.dependencies import get_db
from app.main import app
from app.routers.reports import report_access


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    conn = connect(':memory:')
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def handlers(conn: sqlite3.Connection) -> EventHandlers:
    return EventHandlers(conn)


@pytest.fixture
def claims() -> dict[str, Any]:
    return {'sub': 'usr_seller_1', 'role': 'seller', 'email': 'ana@example.com'}


@pytest.fixture
def client(conn: sqlite3.Connection, claims: dict[str, Any]) -> Iterator[TestClient]:
    # TestClient sem "with" não roda o lifespan, então o consumer Kafka não sobe nos testes
    app.dependency_overrides[get_db] = lambda: conn
    app.dependency_overrides[report_access] = lambda: claims
    yield TestClient(app)
    app.dependency_overrides.clear()


def event(
    event_type: str, data: dict[str, Any], event_id: str = 'evt_1', occurred_at: str = '2026-10-05T10:00:00.000Z'
):
    return {
        'eventId': event_id,
        'type': event_type,
        'version': 1,
        'occurredAt': occurred_at,
        'producer': 'tests',
        'data': data,
    }


def order_paid(order_id: str, items: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    data = {
        'orderId': order_id,
        'buyerId': 'usr_buyer_1',
        'sellerIds': sorted({item['sellerId'] for item in items}),
        'items': items,
        'totalCents': sum(item['quantity'] * item['priceCents'] for item in items),
    }
    return event('order.paid', data, **kwargs)


def product_created(product_id: str, seller_id: str, name: str, price_cents: int, **kwargs: Any) -> dict[str, Any]:
    data = {
        'productId': product_id,
        'sellerId': seller_id,
        'categoryId': 'cat_1',
        'name': name,
        'priceCents': price_cents,
        'stock': 10,
        'active': True,
    }
    return event('product.created', data, **kwargs)


def product_viewed(product_id: str, user_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    return event('product.viewed', {'productId': product_id, 'userId': user_id}, **kwargs)
