"""Agregações puras em pandas. Recebem DataFrames e devolvem listas prontas para o JSON.

Colunas esperadas:
- sales: order_id, product_id, quantity, price_cents, paid_at
- products: product_id, name
- views: product_id, viewed_at
"""

from typing import Any, Literal

import pandas as pd

GroupBy = Literal['day', 'week', 'month']

SALES_COLUMNS = ['order_id', 'product_id', 'quantity', 'price_cents', 'paid_at']
PRODUCT_COLUMNS = ['product_id', 'name']
VIEW_COLUMNS = ['product_id', 'viewed_at']


def sales_series(sales: pd.DataFrame, group_by: GroupBy) -> list[dict[str, Any]]:
    """Série temporal de receita, pedidos e itens vendidos por período."""
    if sales.empty:
        return []
    frame = sales[SALES_COLUMNS].copy()
    frame['revenue_cents'] = frame['quantity'] * frame['price_cents']
    frame['period'] = _period_start(pd.to_datetime(frame['paid_at']), group_by)
    grouped = frame.groupby('period').agg(
        revenue_cents=('revenue_cents', 'sum'),
        orders=('order_id', 'nunique'),
        items_sold=('quantity', 'sum'),
    )
    return [
        {
            'period': period.strftime('%Y-%m-%d'),
            'revenueCents': int(row.revenue_cents),
            'orders': int(row.orders),
            'itemsSold': int(row.items_sold),
        }
        for period, row in grouped.sort_index().iterrows()
    ]


def top_products(sales: pd.DataFrame, products: pd.DataFrame, limit: int) -> dict[str, list[dict[str, Any]]]:
    """Ranking de produtos por receita e por quantidade."""
    if sales.empty:
        return {'byRevenue': [], 'byQuantity': []}
    frame = sales[SALES_COLUMNS].copy()
    frame['revenue_cents'] = frame['quantity'] * frame['price_cents']
    totals = frame.groupby('product_id').agg(revenue_cents=('revenue_cents', 'sum'), items_sold=('quantity', 'sum'))
    totals = _with_names(totals, products)
    return {
        'byRevenue': _ranking(totals.sort_values(['revenue_cents', 'product_id'], ascending=[False, True]), limit),
        'byQuantity': _ranking(totals.sort_values(['items_sold', 'product_id'], ascending=[False, True]), limit),
    }


def views_report(views: pd.DataFrame, sales: pd.DataFrame, products: pd.DataFrame) -> list[dict[str, Any]]:
    """Visualizações por produto e conversão (pedidos / visualizações)."""
    view_counts = views.groupby('product_id').size() if not views.empty else pd.Series(dtype='int64')
    order_counts = sales.groupby('product_id')['order_id'].nunique() if not sales.empty else pd.Series(dtype='int64')
    totals = pd.DataFrame({'views': view_counts, 'orders': order_counts}).fillna(0).astype('int64')
    if totals.empty:
        return []
    totals.index.name = 'product_id'
    # Produto com venda e sem visualização registrada fica com conversão zero, nunca divisão por zero
    totals['conversion_rate'] = (totals['orders'] / totals['views'].where(totals['views'] > 0)).fillna(0.0)
    totals = _with_names(totals, products).sort_values(['views', 'product_id'], ascending=[False, True])
    return [
        {
            'productId': product_id,
            'name': row['name'],
            'views': int(row.views),
            'orders': int(row.orders),
            'conversionRate': round(float(row.conversion_rate), 4),
        }
        for product_id, row in totals.iterrows()
    ]


def series_to_csv(series: list[dict[str, Any]]) -> str:
    columns = ['period', 'revenueCents', 'orders', 'itemsSold']
    return pd.DataFrame(series, columns=columns).to_csv(index=False, lineterminator='\n')


def _period_start(paid_at: pd.Series, group_by: GroupBy) -> pd.Series:
    if group_by == 'day':
        return paid_at.dt.normalize()
    if group_by == 'week':
        return paid_at.dt.to_period('W').dt.start_time
    return paid_at.dt.to_period('M').dt.start_time


def _with_names(totals: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    names = products[PRODUCT_COLUMNS].drop_duplicates('product_id').set_index('product_id')['name']
    joined = totals.join(names, how='left')
    # Produto que ainda não chegou por evento aparece pelo id, sem nome
    joined['name'] = joined['name'].astype('object').where(joined['name'].notna(), None)
    return joined


def _ranking(totals: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    return [
        {
            'productId': product_id,
            'name': row['name'],
            'revenueCents': int(row.revenue_cents),
            'itemsSold': int(row.items_sold),
        }
        for product_id, row in totals.head(limit).iterrows()
    ]
