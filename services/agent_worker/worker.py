import asyncio
import json
import logging
import sys
import os
from aiokafka import AIOKafkaConsumer
from shared.config.settings import get_settings
from shared.events.event_types import EventType

# Setup system environment tracking paths
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinelos.worker")
settings = get_settings()

class AgentRuntimeWorker:
    """Independent background daemon processing production event payloads from Redpanda."""
    def __init__(self):
        self._consumer = None
        self._broker_url = settings.redpanda.brokers
        self._topic = settings.redpanda.topic_agent_events
        self.is_running = False

    async def start(self):
        """Initializes and binds the persistent streaming socket to the broker cluster."""
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._broker_url,
            group_id="sentinelos-agent-workers",  # Enables automatic horizontal scaling across multiple instances
            auto_offset_reset="earliest",         # Guarantees catching up on missed events during down periods
            enable_auto_commit=True
        )
        await self._consumer.start()
        self.is_running = True
        logger.info(f"🚀 SentinelOS Background Runtime Worker active and polling topic: {self._topic}")

        try:
            async for message in self._consumer:
                if not self.is_running:
                    break
                await self._process_message(message)
        except Exception as e:
            logger.error(f"CRITICAL FAULT ENCOUNTERED IN CONSUMER LOOP: {str(e)}")
        finally:
            await self.stop()

    async def _process_message(self, message) -> None:
        """Core message parsing router."""
        try:
            # Decode the message payload bytes back into JSON dict
            payload = json.loads(message.value.decode("utf-8"))
            event_type = payload.get("event_type")
            run_id = payload.get("run_id")
            sequence = payload.get("sequence_number")

            logger.info(f"📥 Received event [{event_type}] for Run {run_id} (Seq: {sequence})")

            # INTERCEPT EVENT TO TRIGGER ASYNC AGENT WORK
            if event_type == EventType.RUN_STARTED.value:
                await self._execute_agent_next_step(run_id, sequence)

        except Exception as e:
            logger.error(f"Failed to process log sequence offset {message.offset}: {str(e)}")

    async def _execute_agent_next_step(self, run_id: str, current_sequence: int) -> None:
        """
        Simulates the background execution boundary.
        This is where our worker will eventually hand control to Ollama/Local LLMs.
        """
        logger.info(f"🧠 Worker activating LLM brain logic for Run {run_id}...")
        await asyncio.sleep(1.5)  # Simulating LLM inference latency
        logger.info(f"✅ Step execution complete for Run {run_id}. Ready to dispatch follow-up event.")

    async def stop(self):
        """Gracefully tears down socket pools."""
        if self._consumer and self.is_running:
            self.is_running = False
            await self._consumer.stop()
            logger.info("Worker daemon consumer cleanly disconnected.")

if __name__ == "__main__":
    # Ensure project root is visible to Python path interpreter
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    worker = AgentRuntimeWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Shutdown signal caught.")