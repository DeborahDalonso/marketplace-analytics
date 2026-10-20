from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from app.auth import require_role
from app.dependencies import get_report_service
from app.envelope import ok
from app.schemas import ReportQuery, SalesQuery, TopProductsQuery
from app.services.reports import ReportService

router = APIRouter(prefix='/reports', tags=['reports'])

report_access = require_role('seller', 'admin')

Claims = Annotated[dict[str, Any], Depends(report_access)]
Service = Annotated[ReportService, Depends(get_report_service)]


@router.get('/sales')
def sales(claims: Claims, service: Service, query: Annotated[SalesQuery, Query()]):
    seller_id = service.resolve_seller(claims, query.seller_id)
    return ok(service.sales_series(query, seller_id))


@router.get('/sales.csv')
def sales_csv(claims: Claims, service: Service, query: Annotated[SalesQuery, Query()]):
    seller_id = service.resolve_seller(claims, query.seller_id)
    from_iso, to_iso = query.range_iso
    filename = f'sales-{from_iso[:10]}-{to_iso[:10]}.csv'
    return Response(
        content=service.sales_csv(query, seller_id),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/top-products')
def top_products(claims: Claims, service: Service, query: Annotated[TopProductsQuery, Query()]):
    seller_id = service.resolve_seller(claims, query.seller_id)
    return ok(service.top_products(query, seller_id))


@router.get('/views')
def views(claims: Claims, service: Service, query: Annotated[ReportQuery, Query()]):
    seller_id = service.resolve_seller(claims, query.seller_id)
    return ok(service.views_report(query, seller_id))
