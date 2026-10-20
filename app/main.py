import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.config import SERVICE_NAME, VERSION, configure_logging, get_settings
from app.consumers.handlers import EventHandlers
from app.consumers.kafka import KafkaConsumerLoop
from app.db import connect, migrate
from app.errors import register_exception_handlers
from app.routers import health, reports

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    conn = connect(settings.db_path)
    applied = migrate(conn)
    logger.info('Banco %s pronto, %d migration(s) aplicada(s)', settings.db_path, applied)

    # O consumer tem a própria conexão; as rotas abrem a delas por requisição
    consumer = KafkaConsumerLoop(settings.kafka_brokers, EventHandlers(conn))
    app.state.consumer = consumer
    task = asyncio.create_task(consumer.run())
    logger.info('%s %s ouvindo na porta %d', SERVICE_NAME, VERSION, settings.port)

    yield

    await consumer.stop()
    task.cancel()
    conn.close()
    logger.info('Serviço encerrado')


app = FastAPI(title=SERVICE_NAME, version=VERSION, lifespan=lifespan)
register_exception_handlers(app)
app.include_router(health.router)
app.include_router(reports.router)


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='0.0.0.0', port=get_settings().port)
