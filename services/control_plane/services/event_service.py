from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from services.event_store.repositories.run_repository import PostgresRunRepository
from services.event_store.repositories.event_repository import PostgresEventRepository
from services.event_store.models.agent_event import AgentEventModel
from services.control_plane.messaging.publisher import EventPublisher  # <--- Added
from shared.contracts.base_event import BaseEvent

class EventService:
    def __init__(self, session: AsyncSession):
        self.run_repo = PostgresRunRepository(session)
        self.event_repo = PostgresEventRepository(session)
        self.publisher = EventPublisher()  # <--- Added

    async def append_event_to_stream(self, event_contract: BaseEvent) -> AgentEventModel:
        """Appends a validated event contract to the database and streams it to the broker."""
        run_aggregate = await self.run_repo.get_by_id(event_contract.run_id)
        if not run_aggregate:
            raise ValueError(f"Target Agent Run Aggregate {event_contract.run_id} does not exist.")
            
        stream = await self.event_repo.get_stream_by_run_id(event_contract.run_id)
        computed_sequence = len(stream) + 1
        
        db_event = AgentEventModel(
            event_id=event_contract.event_id,
            run_id=event_contract.run_id,
            event_type=event_contract.event_type.value,
            sequence_number=computed_sequence,
            payload=event_contract.payload,
            correlation_id=event_contract.correlation_id,
            causation_id=event_contract.causation_id,
            schema_version=event_contract.schema_version
        )
        
        if event_contract.event_type.value in ["RUN_COMPLETED", "RUN_FAILED"]:
            run_aggregate.status = event_contract.event_type.value.replace("RUN_", "")
            await self.run_repo.save(run_aggregate)
            
        saved_row = await self.event_repo.save(db_event)

        # ── STREAM OUT TO BROKER DISTRIBUTED TIER ──
        # Re-map package contract with the updated exact database sequence assigned
        updated_contract = BaseEvent(
            event_id=event_contract.event_id,
            run_id=event_contract.run_id,
            event_type=event_contract.event_type,
            sequence_number=computed_sequence,
            timestamp=event_contract.timestamp,
            payload=event_contract.payload,
            correlation_id=event_contract.correlation_id,
            causation_id=event_contract.causation_id,
            schema_version=event_contract.schema_version
        )
        
        # Fire and forget safely to broker instance
        await self.publisher.publish_event(updated_contract)
            
        return saved_row