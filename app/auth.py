import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.errors import DomainError

logger = logging.getLogger(__name__)

ISSUER = 'marketplace-auth'
JWKS_CACHE_S = 600

bearer = HTTPBearer(auto_error=False)


@lru_cache
def jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=JWKS_CACHE_S)


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Valida assinatura RS256 contra o JWKS do auth e devolve as claims."""
    try:
        signing_key = jwk_client(settings.jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=['RS256'], issuer=ISSUER)
    except jwt.PyJWTError as exc:
        logger.info('Token rejeitado: %s', exc)
        raise DomainError('auth.invalid_token', 401) from exc


def require_role(*roles: str) -> Callable[..., dict[str, Any]]:
    def dependency(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> dict[str, Any]:
        if credentials is None:
            raise DomainError('auth.missing_token', 401)
        claims = decode_token(credentials.credentials, settings)
        if claims.get('role') not in roles:
            raise DomainError('auth.forbidden', 403)
        return claims

    return dependency
