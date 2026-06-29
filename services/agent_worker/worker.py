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

# Import our secure runtime execution manager sandbox
from services.agent_worker.tools.manager import ToolManager

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
        
        # Instantiate the isolated secure tool registry boundary
        self.tool_manager = ToolManager()
        logger.info("SYSTEM_INIT: Worker runtime environment fully configured with ToolManager sandbox.")

    async def start(self):
        """Initializes and binds the persistent streaming socket to the broker cluster."""
        import uuid
        unique_group = f"sentinelos-agent-workers-{uuid.uuid4().hex[:8]}"
        
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._broker_url,
            group_id=unique_group,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            heartbeat_interval_ms=5000,
            session_timeout_ms=30000
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

            # Trigger LLM evaluation when a run starts, or when an external tool output completes
            if event_type in [EventType.RUN_STARTED.value, "TOOL_OUTPUT"]:
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
        
        async for db_session in get_db_session():
            repo = PostgresEventRepository(db_session)
            stream = await repo.get_stream_by_run_id(run_id)
            
            if not stream:
                logger.warning(f"Aborting execution. No chronological event history found for Run {run_id}")
                return
                
            reconstructed_state = ReplayEngine.reconstruct_state(run_id, stream)
            steps_history = reconstructed_state.execution_steps
            
            # 1. Compile available local tooling definitions for prompt inclusion
            tools_context = self.tool_manager.get_tool_definitions_context()
            
            logger.info(f"INFERENCE_DISPATCH: Transmitting event sequence history context pool. steps_count={len(steps_history)} destination=ollama")
            
            # 2. Fire inference query with our dynamic tools payload injected
            llm_decision = await self.llm.generate_reasoning_step(steps_history, tools_context)
            
            action = llm_decision.get("action_type")
            content = llm_decision.get("content")
            
            logger.info(f"INFERENCE_RECEIVE: Decision model response parsed successfully. decision_action={action} payload_summary='{content[:60]}...'")
            
            # Continuous dynamic ledger synchronization index
            next_sequence = len(steps_history) + 1  
            
            # ── CASE 1 & 3: PLAN GENERATION & RUN COMPLETION TERMINALS ──
            if action in ["PLAN_GENERATED", "RUN_COMPLETED"]:
                await self.dispatcher.dispatch_inferred_event(
                    run_id=run_id,
                    event_type=action,
                    content=content,
                    sequence_number=next_sequence
                )
                logger.info(f"COMMAND_DISPATCH: Completed state writeback for active sequence. event_type={action}")

            # ── CASE 2: SECURE SYSTEM TOOL EXECUTION STEP ──
            elif action == "TOOL_CALLED":
                tool_name = llm_decision.get("tool_name")
                arguments = llm_decision.get("arguments") or {}

                # A. Commit the intentional TOOL_CALLED log event back to the Control Plane
                await self.dispatcher.dispatch_inferred_event(
                    run_id=run_id,
                    event_type="TOOL_CALLED",
                    content=f"Agent intent registered: Invoking local utility '{tool_name}' with arguments {json.dumps(arguments)}.",
                    sequence_number=next_sequence
                )

                # B. Safely execute the real system operation behind the firewalled registry sandbox
                tool_output = await self.tool_manager.execute_tool(tool_name, arguments)

                # C. Increment the slot sequence value to account for the incoming tool output write
                output_sequence = next_sequence + 1
                
                # D. Ship the tool execution data payload straight back to the database ledger
                await self.dispatcher.dispatch_inferred_event(
                    run_id=run_id,
                    event_type="TOOL_OUTPUT_RECEIVED",
                    content=f"Execution block resolved for tool '{tool_name}'. Output: {json.dumps(tool_output)}",
                    sequence_number=output_sequence
                )
                logger.info(f"COMMAND_DISPATCH: Roundtrip tool transaction appended successfully. next_sequence={output_sequence}")

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