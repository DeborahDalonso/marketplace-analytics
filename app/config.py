import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_NAME = 'marketplace-analytics'
VERSION = '1.0.0'


class Settings(BaseSettings):
    # .env.local sobrescreve .env e fica fora do git
    model_config = SettingsConfigDict(env_file=('.env', '.env.local'), extra='ignore')

    port: int = 3005
    kafka_brokers: str = 'localhost:19092'
    auth_url: str = 'http://localhost:3003'
    db_path: str = 'data/analytics.db'
    log_level: str = 'info'

    @property
    def jwks_url(self) -> str:
        return f'{self.auth_url.rstrip("/")}/.well-known/jwks.json'


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        force=True,
    )
