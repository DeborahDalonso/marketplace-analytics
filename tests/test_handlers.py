import pytest

from tests.conftest import event, order_paid, product_created, product_viewed

ITEMS = [
    {'productId': 'prd_a', 'sellerId': 'usr_seller_1', 'quantity': 2, 'priceCents': 1000},
    {'productId': 'prd_b', 'sellerId': 'usr_seller_2', 'quantity': 1, 'priceCents': 500},
]


class TestEventHandlersHandle:
    def test_grava_uma_venda_por_item_do_pedido(self, handlers, conn):
        assert handlers.handle(order_paid('ord_1', ITEMS)) is True

        rows = conn.execute('SELECT * FROM sales ORDER BY product_id').fetchall()
        assert [dict(row) for row in rows] == [
            {
                'id': 1,
                'order_id': 'ord_1',
                'product_id': 'prd_a',
                'seller_id': 'usr_seller_1',
                'buyer_id': 'usr_buyer_1',
                'quantity': 2,
                'price_cents': 1000,
                'paid_at': '2026-10-05T10:00:00',
            },
            {
                'id': 2,
                'order_id': 'ord_1',
                'product_id': 'prd_b',
                'seller_id': 'usr_seller_2',
                'buyer_id': 'usr_buyer_1',
                'quantity': 1,
                'price_cents': 500,
                'paid_at': '2026-10-05T10:00:00',
            },
        ]

    def test_ignora_evento_com_mesmo_event_id(self, handlers, conn):
        handlers.handle(order_paid('ord_1', ITEMS, event_id='evt_dup'))

        assert handlers.handle(order_paid('ord_1', ITEMS, event_id='evt_dup')) is False
        assert conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == 2
        assert handlers.processed.count() == 1

    def test_converte_occurred_at_com_fuso_para_utc(self, handlers, conn):
        handlers.handle(order_paid('ord_1', ITEMS, occurred_at='2026-10-05T07:00:00-03:00'))

        assert conn.execute('SELECT paid_at FROM sales').fetchone()[0] == '2026-10-05T10:00:00'

    def test_cria_produto(self, handlers):
        handlers.handle(product_created('prd_a', 'usr_seller_1', 'Fone', 1990))

        assert handlers.products.find('prd_a') == {
            'product_id': 'prd_a',
            'seller_id': 'usr_seller_1',
            'category_id': 'cat_1',
            'name': 'Fone',
            'price_cents': 1990,
            'created_at': '2026-10-05T10:00:00',
        }

    def test_atualiza_produto_mantendo_created_at(self, handlers):
        handlers.handle(product_created('prd_a', 'usr_seller_1', 'Fone', 1990, event_id='evt_1'))
        updated = product_created(
            'prd_a', 'usr_seller_1', 'Fone Pro', 2990, event_id='evt_2', occurred_at='2026-10-09T10:00:00Z'
        )
        updated['type'] = 'product.updated'

        handlers.handle(updated)

        product = handlers.products.find('prd_a')
        assert product['name'] == 'Fone Pro'
        assert product['price_cents'] == 2990
        assert product['created_at'] == '2026-10-05T10:00:00'

    def test_registra_visualizacao_sem_usuario(self, handlers, conn):
        handlers.handle(product_viewed('prd_a'))

        row = conn.execute('SELECT product_id, user_id, viewed_at FROM product_views').fetchone()
        assert dict(row) == {'product_id': 'prd_a', 'user_id': None, 'viewed_at': '2026-10-05T10:00:00'}

    def test_ignora_tipo_desconhecido_sem_marcar_como_processado(self, handlers):
        assert handlers.handle(event('order.cancelled', {'orderId': 'ord_1'})) is False
        assert handlers.processed.count() == 0

    def test_desfaz_a_marca_quando_a_gravacao_falha(self, handlers, conn):
        broken = order_paid('ord_1', ITEMS)
        del broken['data']['items'][0]['priceCents']

        with pytest.raises(KeyError):
            handlers.handle(broken)

        assert handlers.processed.count() == 0
        assert conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == 0
