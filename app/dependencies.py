import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.db import connect
from app.models.products import ProductModel
from app.models.sales import SaleModel
from app.models.views import ProductViewModel
from app.services.reports import ReportService


def get_db(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[sqlite3.Connection]:
    # Uma conexão por requisição: SQLite abre rápido e evita dividir conexão entre threads
    conn = connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_report_service(conn: Annotated[sqlite3.Connection, Depends(get_db)]) -> ReportService:
    return ReportService(SaleModel(conn), ProductModel(conn), ProductViewModel(conn))
