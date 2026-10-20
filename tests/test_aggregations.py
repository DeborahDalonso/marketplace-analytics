import pandas as pd

from app.services.aggregations import sales_series, series_to_csv, top_products, views_report

SALES = pd.DataFrame(
    [
        # order, product, qty, price, paid_at
        ('ord_1', 'prd_a', 2, 1000, '2026-10-05T10:00:00'),
        ('ord_1', 'prd_b', 1, 500, '2026-10-05T10:00:00'),
        ('ord_2', 'prd_a', 1, 1000, '2026-10-05T18:30:00'),
        ('ord_3', 'prd_b', 4, 500, '2026-10-07T09:00:00'),
        ('ord_4', 'prd_c', 1, 9900, '2026-11-02T12:00:00'),
    ],
    columns=['order_id', 'product_id', 'quantity', 'price_cents', 'paid_at'],
)

PRODUCTS = pd.DataFrame(
    [('prd_a', 'Fone'), ('prd_b', 'Cabo'), ('prd_c', 'Teclado')],
    columns=['product_id', 'name'],
)

VIEWS = pd.DataFrame(
    [
        ('prd_a', '2026-10-04T10:00:00'),
        ('prd_a', '2026-10-05T10:00:00'),
        ('prd_a', '2026-10-05T11:00:00'),
        ('prd_a', '2026-10-06T11:00:00'),
        ('prd_d', '2026-10-06T11:00:00'),
    ],
    columns=['product_id', 'viewed_at'],
)

EMPTY_SALES = pd.DataFrame(columns=SALES.columns)
EMPTY_VIEWS = pd.DataFrame(columns=VIEWS.columns)


class TestSalesSeries:
    def test_agrupa_vendas_por_dia(self):
        series = sales_series(SALES, 'day')

        assert [row['period'] for row in series] == ['2026-10-05', '2026-10-07', '2026-11-02']
        assert series[0] == {'period': '2026-10-05', 'revenueCents': 3500, 'orders': 2, 'itemsSold': 4}
        assert series[1] == {'period': '2026-10-07', 'revenueCents': 2000, 'orders': 1, 'itemsSold': 4}

    def test_agrupa_vendas_por_semana_a_partir_da_segunda_feira(self):
        series = sales_series(SALES, 'week')

        assert [row['period'] for row in series] == ['2026-10-05', '2026-11-02']
        assert series[0]['revenueCents'] == 5500
        assert series[0]['orders'] == 3
        assert series[0]['itemsSold'] == 8

    def test_agrupa_vendas_por_mes(self):
        series = sales_series(SALES, 'month')

        assert series == [
            {'period': '2026-10-01', 'revenueCents': 5500, 'orders': 3, 'itemsSold': 8},
            {'period': '2026-11-01', 'revenueCents': 9900, 'orders': 1, 'itemsSold': 1},
        ]

    def test_conta_pedido_com_varios_itens_uma_vez(self):
        series = sales_series(SALES[SALES['order_id'] == 'ord_1'], 'day')

        assert series[0]['orders'] == 1
        assert series[0]['itemsSold'] == 3

    def test_devolve_lista_vazia_sem_vendas(self):
        assert sales_series(EMPTY_SALES, 'day') == []


class TestTopProducts:
    def test_ordena_por_receita_e_por_quantidade(self):
        ranking = top_products(SALES, PRODUCTS, limit=10)

        assert [row['productId'] for row in ranking['byRevenue']] == ['prd_c', 'prd_a', 'prd_b']
        assert [row['productId'] for row in ranking['byQuantity']] == ['prd_b', 'prd_a', 'prd_c']
        assert ranking['byRevenue'][1] == {'productId': 'prd_a', 'name': 'Fone', 'revenueCents': 3000, 'itemsSold': 3}

    def test_respeita_o_limite(self):
        ranking = top_products(SALES, PRODUCTS, limit=1)

        assert len(ranking['byRevenue']) == 1
        assert len(ranking['byQuantity']) == 1

    def test_produto_sem_cadastro_aparece_sem_nome(self):
        ranking = top_products(SALES, PRODUCTS[PRODUCTS['product_id'] != 'prd_c'], limit=10)

        assert ranking['byRevenue'][0]['productId'] == 'prd_c'
        assert ranking['byRevenue'][0]['name'] is None

    def test_devolve_rankings_vazios_sem_vendas(self):
        assert top_products(EMPTY_SALES, PRODUCTS, limit=10) == {'byRevenue': [], 'byQuantity': []}


class TestViewsReport:
    def test_calcula_conversao_por_produto(self):
        report = views_report(VIEWS, SALES, PRODUCTS)
        by_id = {row['productId']: row for row in report}

        assert by_id['prd_a'] == {'productId': 'prd_a', 'name': 'Fone', 'views': 4, 'orders': 2, 'conversionRate': 0.5}

    def test_conversao_fica_zero_quando_nao_ha_visualizacao(self):
        report = views_report(VIEWS, SALES, PRODUCTS)
        by_id = {row['productId']: row for row in report}

        assert by_id['prd_b']['views'] == 0
        assert by_id['prd_b']['orders'] == 2
        assert by_id['prd_b']['conversionRate'] == 0.0

    def test_produto_visto_sem_venda_tem_conversao_zero(self):
        report = views_report(VIEWS, SALES, PRODUCTS)
        by_id = {row['productId']: row for row in report}

        assert by_id['prd_d'] == {'productId': 'prd_d', 'name': None, 'views': 1, 'orders': 0, 'conversionRate': 0.0}

    def test_ordena_por_visualizacoes(self):
        report = views_report(VIEWS, SALES, PRODUCTS)

        assert report[0]['productId'] == 'prd_a'

    def test_devolve_lista_vazia_sem_dados(self):
        assert views_report(EMPTY_VIEWS, EMPTY_SALES, PRODUCTS) == []


class TestSeriesToCsv:
    def test_gera_cabecalho_e_linhas(self):
        csv = series_to_csv(sales_series(SALES, 'month'))

        assert csv == 'period,revenueCents,orders,itemsSold\n2026-10-01,5500,3,8\n2026-11-01,9900,1,1\n'

    def test_gera_so_cabecalho_sem_dados(self):
        assert series_to_csv([]) == 'period,revenueCents,orders,itemsSold\n'
