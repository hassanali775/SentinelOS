import json
import logging
from uuid import UUID
from aiokafka import AIOKafkaProducer
from shared.config.settings import get_settings
from shared.contracts.base_event import BaseEvent

logger = logging.getLogger("sentinelos.publisher")
settings = get_settings()

class EventPublisher:
    """Production-grade asynchronous event publisher for Redpanda/Kafka streams."""
    def __init__(self):
        self._producer = None
        self._broker_url = settings.redpanda.brokers
        self._topic = settings.redpanda.topic_agent_events

    async def start(self):
        """Initializes the underlying connection pool to the message broker cluster."""
        if not self._producer:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._broker_url,
                client_id="sentinelos-control-plane",
                retry_backoff_ms=500
                # Removed max_block_ms to match correct aiokafka API specification
            )
            await self._producer.start()
            logger.info(f"Asynchronous event stream publisher bound to cluster: {self._broker_url}")

    async def stop(self):
        """Gracefully flushes remaining buffers and closes broker socket connections."""
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Event stream publisher disconnected from broker cluster.")

    async def publish_event(self, event: BaseEvent) -> None:
        """
        Publishes a schema-validated domain event to the broker topic.
        Uses the run_id as the message key to guarantee partition ordering.
        """
        if not self._producer:
            await self.start()

        # Serialize Pydantic model directly to optimized JSON bytes
        # Handles UUID and Datetime conversions cleanly via Pydantic model dump
        message_json = event.model_dump_json()
        message_bytes = message_json.encode("utf-8")
        key_bytes = str(event.run_id).encode("utf-8")

        try:
            # Partition routing is guaranteed stable by hashing the run_id key
            await self._producer.send_and_wait(
                topic=self._topic,
                value=message_bytes,
                key=key_bytes
            )
        except Exception as e:
            logger.error(f"FALURE TO TRANSMIT FACT TO BROKER LOG SYSTEM: {str(e)}")
            raise