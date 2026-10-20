import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.consumers.handlers import TOPICS, EventHandlers

logger = logging.getLogger(__name__)

GROUP_ID = 'marketplace-analytics'
RETRY_DELAY_S = 5


class KafkaConsumerLoop:
    """Consome os tópicos de interesse e entrega cada envelope ao EventHandlers.

    Nunca derruba o processo: falha de conexão vira retry, falha em mensagem vira log.
    """

    def __init__(self, brokers: str, handlers: EventHandlers) -> None:
        self.brokers = brokers
        self.handlers = handlers
        self.connected = False
        self._stopping = False
        self._consumer: AIOKafkaConsumer | None = None

    async def run(self) -> None:
        while not self._stopping:
            try:
                await self._consume()
            except asyncio.CancelledError:
                break
            except KafkaError as exc:
                self.connected = False
                logger.warning('Kafka indisponível (%s); nova tentativa em %ss', exc, RETRY_DELAY_S)
                await asyncio.sleep(RETRY_DELAY_S)
            except Exception:
                self.connected = False
                logger.exception('Falha inesperada no consumer; reiniciando em %ss', RETRY_DELAY_S)
                await asyncio.sleep(RETRY_DELAY_S)

    async def stop(self) -> None:
        self._stopping = True
        if self._consumer is not None:
            await self._consumer.stop()
        self.connected = False

    async def _consume(self) -> None:
        self._consumer = AIOKafkaConsumer(
            *TOPICS,
            bootstrap_servers=self.brokers,
            group_id=GROUP_ID,
            enable_auto_commit=False,
            auto_offset_reset='earliest',
        )
        await self._consumer.start()
        self.connected = True
        logger.info('Consumer conectado em %s, tópicos %s', self.brokers, ', '.join(TOPICS))
        try:
            async for message in self._consumer:
                self._handle_message(message.topic, message.value)
                # Commit só depois de gravar: se o processo cair antes, o evento volta e a
                # tabela processed_events segura a repetição
                await self._consumer.commit()
        finally:
            await self._consumer.stop()
            self.connected = False

    def _handle_message(self, topic: str, raw: bytes | None) -> None:
        try:
            event = json.loads(raw or b'')
        except ValueError:
            logger.error('Mensagem inválida em %s descartada (JSON malformado)', topic)
            return
        try:
            self.handlers.handle(event)
        except (KeyError, TypeError) as exc:
            logger.error('Envelope fora do contrato em %s descartado: campo %s', topic, exc)
        except Exception:
            logger.exception('Falha ao processar evento %s em %s', event.get('eventId'), topic)
