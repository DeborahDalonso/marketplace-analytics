from tests.conftest import order_paid, product_created, product_viewed

RANGE = {'from': '2026-10-01', 'to': '2026-10-31'}


def seed(handlers):
    handlers.handle(product_created('prd_a', 'usr_seller_1', 'Fone', 1000, event_id='evt_p1'))
    handlers.handle(product_created('prd_b', 'usr_seller_2', 'Cabo', 500, event_id='evt_p2'))
    handlers.handle(
        order_paid(
            'ord_1',
            [
                {'productId': 'prd_a', 'sellerId': 'usr_seller_1', 'quantity': 2, 'priceCents': 1000},
                {'productId': 'prd_b', 'sellerId': 'usr_seller_2', 'quantity': 1, 'priceCents': 500},
            ],
            event_id='evt_o1',
        )
    )
    handlers.handle(
        order_paid(
            'ord_2',
            [{'productId': 'prd_a', 'sellerId': 'usr_seller_1', 'quantity': 1, 'priceCents': 1000}],
            event_id='evt_o2',
            occurred_at='2026-10-12T10:00:00Z',
        )
    )
    handlers.handle(product_viewed('prd_a', event_id='evt_v1'))
    handlers.handle(product_viewed('prd_a', 'usr_buyer_1', event_id='evt_v2'))
    handlers.handle(product_viewed('prd_b', event_id='evt_v3'))


class TestGetReportsSales:
    def test_vendedor_ve_a_propria_serie_por_dia(self, client, handlers):
        seed(handlers)

        response = client.get('/reports/sales', params={**RANGE, 'sellerId': 'usr_seller_1'})

        assert response.status_code == 200
        assert response.json() == {
            'success': True,
            'message': None,
            'data': [
                {'period': '2026-10-05', 'revenueCents': 2000, 'orders': 1, 'itemsSold': 2},
                {'period': '2026-10-12', 'revenueCents': 1000, 'orders': 1, 'itemsSold': 1},
            ],
        }

    def test_agrupa_por_mes_quando_pedido(self, client, handlers):
        seed(handlers)

        response = client.get('/reports/sales', params={**RANGE, 'sellerId': 'usr_seller_1', 'groupBy': 'month'})

        assert response.json()['data'] == [{'period': '2026-10-01', 'revenueCents': 3000, 'orders': 2, 'itemsSold': 3}]

    def test_recusa_vendedor_consultando_outro_seller_id(self, client):
        response = client.get('/reports/sales', params={**RANGE, 'sellerId': 'usr_seller_2'})

        assert response.status_code == 403
        assert response.json() == {
            'success': False,
            'message': 'Vendedor só consulta os próprios relatórios',
            'errors': [],
        }

    def test_exige_seller_id_para_vendedor(self, client):
        response = client.get('/reports/sales', params=RANGE)

        assert response.status_code == 422
        assert response.json()['message'] == 'Informe o sellerId para consultar relatórios'

    def test_admin_ve_tudo_sem_filtro(self, client, handlers, claims):
        seed(handlers)
        claims.update({'sub': 'usr_admin', 'role': 'admin'})

        response = client.get('/reports/sales', params={**RANGE, 'groupBy': 'month'})

        assert response.status_code == 200
        assert response.json()['data'] == [{'period': '2026-10-01', 'revenueCents': 3500, 'orders': 2, 'itemsSold': 4}]

    def test_admin_filtra_por_qualquer_vendedor(self, client, handlers, claims):
        seed(handlers)
        claims.update({'sub': 'usr_admin', 'role': 'admin'})

        response = client.get('/reports/sales', params={**RANGE, 'sellerId': 'usr_seller_2', 'groupBy': 'month'})

        assert response.json()['data'] == [{'period': '2026-10-01', 'revenueCents': 500, 'orders': 1, 'itemsSold': 1}]

    def test_recusa_group_by_invalido_com_422(self, client):
        response = client.get('/reports/sales', params={**RANGE, 'sellerId': 'usr_seller_1', 'groupBy': 'year'})

        assert response.status_code == 422
        assert response.json()['success'] is False
        assert response.json()['errors'][0]['field'] == 'groupBy'

    def test_recusa_intervalo_invertido(self, client):
        response = client.get(
            '/reports/sales', params={'from': '2026-10-31', 'to': '2026-10-01', 'sellerId': 'usr_seller_1'}
        )

        assert response.status_code == 422
        assert response.json()['message'] == 'A data inicial precisa ser anterior à data final'

    def test_usa_ultimos_trinta_dias_sem_datas(self, client):
        response = client.get('/reports/sales', params={'sellerId': 'usr_seller_1'})

        assert response.status_code == 200
        assert response.json()['data'] == []


class TestGetReportsSalesCsv:
    def test_devolve_csv_com_content_disposition(self, client, handlers):
        seed(handlers)

        response = client.get('/reports/sales.csv', params={**RANGE, 'sellerId': 'usr_seller_1', 'groupBy': 'month'})

        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/csv; charset=utf-8'
        assert response.headers['content-disposition'] == 'attachment; filename="sales-2026-10-01-2026-10-31.csv"'
        assert response.text == 'period,revenueCents,orders,itemsSold\n2026-10-01,3000,2,3\n'

    def test_aplica_a_mesma_regra_de_acesso(self, client):
        response = client.get('/reports/sales.csv', params={**RANGE, 'sellerId': 'usr_seller_2'})

        assert response.status_code == 403


class TestGetReportsTopProducts:
    def test_lista_rankings_do_vendedor(self, client, handlers):
        seed(handlers)

        response = client.get('/reports/top-products', params={**RANGE, 'sellerId': 'usr_seller_1'})

        assert response.status_code == 200
        assert response.json()['data'] == {
            'byRevenue': [{'productId': 'prd_a', 'name': 'Fone', 'revenueCents': 3000, 'itemsSold': 3}],
            'byQuantity': [{'productId': 'prd_a', 'name': 'Fone', 'revenueCents': 3000, 'itemsSold': 3}],
        }

    def test_recusa_limite_fora_da_faixa(self, client):
        response = client.get('/reports/top-products', params={**RANGE, 'sellerId': 'usr_seller_1', 'limit': 0})

        assert response.status_code == 422
        assert response.json()['errors'][0]['field'] == 'limit'


class TestGetReportsViews:
    def test_lista_visualizacoes_e_conversao_do_vendedor(self, client, handlers):
        seed(handlers)

        response = client.get('/reports/views', params={**RANGE, 'sellerId': 'usr_seller_1'})

        assert response.status_code == 200
        assert response.json()['data'] == [
            {'productId': 'prd_a', 'name': 'Fone', 'views': 2, 'orders': 2, 'conversionRate': 1.0},
        ]

    def test_admin_ve_produtos_de_todos_os_vendedores(self, client, handlers, claims):
        seed(handlers)
        claims.update({'sub': 'usr_admin', 'role': 'admin'})

        response = client.get('/reports/views', params=RANGE)

        assert [row['productId'] for row in response.json()['data']] == ['prd_a', 'prd_b']


class TestRotasInexistentes:
    def test_responde_404_no_envelope(self, client):
        response = client.get('/reports/nada')

        assert response.status_code == 404
        assert response.json() == {'success': False, 'message': 'Rota não encontrada', 'errors': []}
