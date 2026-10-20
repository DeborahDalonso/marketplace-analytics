from typing import Any

import pandas as pd

from app.errors import DomainError
from app.models.products import ProductModel
from app.models.sales import SaleModel
from app.models.views import ProductViewModel
from app.schemas import ReportQuery, SalesQuery, TopProductsQuery
from app.services import aggregations


class ReportService:
    def __init__(self, sales: SaleModel, products: ProductModel, views: ProductViewModel) -> None:
        self.sales = sales
        self.products = products
        self.product_views = views

    def resolve_seller(self, claims: dict[str, Any], seller_id: str | None) -> str | None:
        """Admin filtra por quem quiser; vendedor só vê o próprio id, e precisa informá-lo."""
        if claims.get('role') == 'admin':
            return seller_id
        if seller_id is None:
            raise DomainError('report.seller_required', 422)
        if seller_id != claims.get('sub'):
            raise DomainError('report.forbidden_seller', 403)
        return seller_id

    def sales_series(self, query: SalesQuery, seller_id: str | None) -> list[dict[str, Any]]:
        return aggregations.sales_series(self._sales_frame(query, seller_id), query.group_by)

    def sales_csv(self, query: SalesQuery, seller_id: str | None) -> str:
        return aggregations.series_to_csv(self.sales_series(query, seller_id))

    def top_products(self, query: TopProductsQuery, seller_id: str | None) -> dict[str, list[dict[str, Any]]]:
        sales = self._sales_frame(query, seller_id)
        return aggregations.top_products(sales, self._products_frame(seller_id), query.limit)

    def views_report(self, query: ReportQuery, seller_id: str | None) -> list[dict[str, Any]]:
        from_iso, to_iso = query.range_iso
        views = pd.DataFrame(self.product_views.fetch(from_iso, to_iso, seller_id), columns=aggregations.VIEW_COLUMNS)
        return aggregations.views_report(views, self._sales_frame(query, seller_id), self._products_frame(seller_id))

    def _sales_frame(self, query: ReportQuery, seller_id: str | None) -> pd.DataFrame:
        from_iso, to_iso = query.range_iso
        return pd.DataFrame(self.sales.fetch(from_iso, to_iso, seller_id), columns=aggregations.SALES_COLUMNS)

    def _products_frame(self, seller_id: str | None) -> pd.DataFrame:
        return pd.DataFrame(self.products.fetch(seller_id), columns=aggregations.PRODUCT_COLUMNS)
