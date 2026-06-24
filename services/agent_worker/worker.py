import sys
import os
import asyncio
import json
import logging

# Dynamically inject project root at the absolute top before internal imports evaluate
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from aiokafka import AIOKafkaConsumer
from shared.config.settings import get_settings
from shared.events.event_types import EventType
from services.event_store.database import get_db_session
from services.event_store.repositories.event_repository import PostgresEventRepository
from services.replay_engine.engine import ReplayEngine
from services.agent_worker.providers.ollama import OllamaProvider
from services.agent_worker.messaging.dispatcher import CommandDispatcher

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
        self.llm = OllamaProvider(model_name="llama3.2")
        self.dispatcher = CommandDispatcher()

    async def start(self):
        """Initializes and binds the persistent streaming socket to the broker cluster."""
        import uuid
        # Generating a unique group ID suffix bypasses sticky consumer partition assignment holds
        unique_group = f"sentinelos-agent-workers-{uuid.uuid4().hex[:8]}"
        
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._broker_url,
            group_id=unique_group,
            auto_offset_reset="earliest",  # Scans the topic from the beginning to catch historical steps
            enable_auto_commit=True
        )
        await self._consumer.start()
        self.is_running = True
        logger.info(f"SYSTEM_INIT: SentinelOS background runtime worker active. group_id={unique_group} topic={self._topic}")

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
            payload = json.loads(message.value.decode("utf-8"))
            event_type = payload.get("event_type")
            run_id = payload.get("run_id")

            logger.info(f"STREAM_CONSUME: Intercepted broker log segment. event_type={event_type} run_id={run_id} offset={message.offset}")

            # Trigger active LLM evaluation when a run initializes, a tool executes, or output drops
            if event_type in [EventType.RUN_STARTED.value, "TOOL_OUTPUT_RECEIVED", "TOOL_CALLED"]:
                await self._execute_agent_next_step(run_id)

        except Exception as e:
            logger.error(f"Failed to process log sequence offset {message.offset}: {str(e)}")

    async def _execute_agent_next_step(self, run_id_str: str) -> None:
        """
        Gathers database facts, reconstructs the timeline dynamically,
        and prompts the local LLM brain to decide the next infrastructure step.
        """
        import uuid
        run_id = uuid.UUID(run_id_str)
        
        logger.info(f"STATE_REPLAY: Reconstructing chronological state timeline. run_id={run_id}")
        
        # Open an independent database session context block for the background worker thread
        async for db_session in get_db_session():
            repo = PostgresEventRepository(db_session)
            stream = await repo.get_stream_by_run_id(run_id)
            
            if not stream:
                logger.warning(f"Aborting execution. No chronological event history found for Run {run_id}")
                return
                
            # Compile current state view on the fly using our pure mathematical ReplayEngine reducer
            reconstructed_state = ReplayEngine.reconstruct_state(run_id, stream)
            steps_history = reconstructed_state.execution_steps
            
            logger.info(f"INFERENCE_DISPATCH: Transmitting event sequence history context pool. steps_count={len(steps_history)} destination=ollama")
            
            # Fire non-blocking inference query to local model
            llm_decision = await self.llm.generate_reasoning_step(steps_history)
            
            action = llm_decision.get("action_type")
            content = llm_decision.get("content")
            
            logger.info(f"INFERENCE_RECEIVE: Decision model response parsed successfully. decision_action={action} payload_summary='{content[:60]}...'")
            
           # ── EXECUTE AUTONOMOUS COMMAND LOOP WRITEBACK ──
            next_sequence = len(steps_history) + 1  # Calculate next sequential ledger slot
            
            if action in ["PLAN_GENERATED", "TOOL_CALLED"]:
                await self.dispatcher.dispatch_inferred_event(
                    run_id=run_id,
                    event_type=action,
                    content=content,
                    sequence_number=next_sequence  # Pass it through to match API criteria
                )
            elif action == "RUN_COMPLETED":
                await self.dispatcher.dispatch_inferred_event(
                    run_id=run_id,
                    event_type="RUN_COMPLETED",
                    content="Autonomous task chain finished successfully by local model selection.",
                    sequence_number=next_sequence  # Pass it through to match API criteria
                )
            break

    async def stop(self):
        """Gracefully tears down socket pools."""
        if self._consumer and self.is_running:
            self.is_running = False
            await self._consumer.stop()
            logger.info("Worker daemon consumer cleanly disconnected.")

if __name__ == "__main__":
    worker = AgentRuntimeWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Shutdown signal caught. Exiting.")