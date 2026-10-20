import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.envelope import fail

logger = logging.getLogger(__name__)

# Mensagens ao cliente ficam aqui, nunca espalhadas pelo código
MESSAGES = {
    'auth.missing_token': 'Token de acesso não informado',
    'auth.invalid_token': 'Token de acesso inválido ou expirado',
    'auth.forbidden': 'Perfil sem permissão para este recurso',
    'report.seller_required': 'Informe o sellerId para consultar relatórios',
    'report.forbidden_seller': 'Vendedor só consulta os próprios relatórios',
    'report.invalid_range': 'A data inicial precisa ser anterior à data final',
}

HTTP_MESSAGES = {
    404: 'Rota não encontrada',
    405: 'Método não permitido',
}


class DomainError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status

    @property
    def message(self) -> str:
        return MESSAGES.get(self.code, self.code)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=fail(exc.message))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{'field': _field_name(err['loc']), 'message': err['msg']} for err in exc.errors()]
        return JSONResponse(status_code=422, content=fail('Parâmetros inválidos', errors))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = HTTP_MESSAGES.get(exc.status_code, 'Erro na requisição')
        return JSONResponse(status_code=exc.status_code, content=fail(message))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # A causa técnica fica no log; o cliente recebe só o genérico
        logger.exception('Erro não tratado em %s %s', request.method, request.url.path)
        return JSONResponse(status_code=500, content=fail('Erro interno do servidor'))


def _field_name(loc: tuple) -> str:
    parts = [str(part) for part in loc if part not in ('query', 'body', 'path', 'header')]
    return '.'.join(parts) or 'request'
