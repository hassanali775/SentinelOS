import json
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from aiokafka import AIOKafkaProducer

from services.event_store.repositories.run_repository import PostgresRunRepository
from services.event_store.repositories.event_repository import PostgresEventRepository
from services.event_store.models.agent_run import AgentRunModel
from services.event_store.models.agent_event import AgentEventModel
from shared.contracts.base_event import BaseEvent
from shared.events.event_types import EventType
from shared.config.settings import get_settings
from shared.domain.execution_states import ExecutionStatus

settings = get_settings()

class RunService:
    def __init__(self, session: AsyncSession):
        self.run_repo = PostgresRunRepository(session)
        self.event_repo = PostgresEventRepository(session)
        self.broker_url = settings.redpanda.brokers
        self.topic = settings.redpanda.topic_agent_events

    async def create_new_run(self, agent_id: UUID, metadata: dict = None) -> AgentRunModel:
        """
        Executes the initial transactional command boundary:
        Creates the Aggregate Root, saves to Postgres, and broadcasts the fact to Redpanda.
        """
        run_id = uuid4()
        correlation_id = uuid4()
        
        # 1. Initialize our Aggregate Root state tracker
        run_aggregate = AgentRunModel(
            run_id=run_id,
            agent_id=agent_id,
            status=ExecutionStatus.PENDING.value,
            version=1,
            metadata_json=metadata or {}
        )
        
        # 2. Build our explicit immutable domain event payload
        started_event = AgentEventModel(
            event_id=uuid4(),
            run_id=run_id,
            event_type=EventType.RUN_STARTED.value,
            sequence_number=1,
            payload={"message": f"Agent execution run initialized for identity {run_id}"},
            correlation_id=correlation_id,
            causation_id=None,
            schema_version=1
        )
        
        # 3. Persist down to Postgres transaction block
        await self.run_repo.save(run_aggregate)
        await self.event_repo.save(started_event)
        
        # 4. ── DISTRIBUTED EMISSION LAYER ──
        # Broadcast the event payload to Redpanda asynchronously to notify the background worker
        producer = AIOKafkaProducer(bootstrap_servers=self.broker_url)
        await producer.start()
        try:
            event_payload = {
                "event_id": str(started_event.event_id),
                "run_id": str(run_id),
                "event_type": EventType.RUN_STARTED.value,
                "sequence_number": 1,
                "correlation_id": str(correlation_id),
                "payload": started_event.payload
            }
            
            # Serialize payload to binary bytes before wire transmission
            await producer.send_and_wait(
                topic=self.topic,
                value=json.dumps(event_payload).encode("utf-8"),
                key=str(run_id).encode("utf-8")
            )
        finally:
            await producer.stop()
        
        return run_aggregate