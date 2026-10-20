import logging
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config import SERVICE_NAME, VERSION
from app.dependencies import get_db
from app.envelope import ok

logger = logging.getLogger(__name__)

router = APIRouter(tags=['health'])


@router.get('/health')
def health(request: Request, conn: Annotated[sqlite3.Connection, Depends(get_db)]) -> JSONResponse:
    consumer = getattr(request.app.state, 'consumer', None)
    checks = {
        'sqlite': _sqlite_status(conn),
        'kafka': 'ok' if consumer is not None and consumer.connected else 'down',
    }
    status = 200 if all(value == 'ok' for value in checks.values()) else 503
    return JSONResponse(status_code=status, content=ok({'service': SERVICE_NAME, 'version': VERSION, **checks}))


def _sqlite_status(conn: sqlite3.Connection) -> str:
    # Health é a única leitura que pode engolir a exceção: o resultado dela é o próprio status
    try:
        conn.execute('SELECT 1 FROM schema_migrations LIMIT 1')
        return 'ok'
    except sqlite3.Error as exc:
        logger.warning('SQLite indisponível no health: %s', exc)
        return 'down'
