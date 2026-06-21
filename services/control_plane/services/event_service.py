from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from services.event_store.repositories.run_repository import PostgresRunRepository
from services.event_store.repositories.event_repository import PostgresEventRepository
from services.event_store.models.agent_event import AgentEventModel
from shared.contracts.base_event import BaseEvent

class EventService:
    def __init__(self, session: AsyncSession):
        self.run_repo = PostgresRunRepository(session)
        self.event_repo = PostgresEventRepository(session)

    async def append_event_to_stream(self, event_contract: BaseEvent) -> AgentEventModel:
        """
        Appends an immutable schema verified event tracking contract directly to the persistence ledger.
        """
        # 1. Ensure the Aggregate Root actually exists
        run_aggregate = await self.run_repo.get_by_id(event_contract.run_id)
        if not run_aggregate:
            raise ValueError(f"Target Agent Run Aggregate {event_contract.run_id} does not exist.")
            
        # 2. Re-fetch current chronological event history length to compute sequence
        stream = await self.event_repo.get_stream_by_run_id(event_contract.run_id)
        computed_sequence = len(stream) + 1
        
        # 3. Create database row structure mapping explicit metadata constraints
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
        
        # 4. Modify aggregate root metadata tracking state
        if event_contract.event_type.value in ["RUN_COMPLETED", "RUN_FAILED"]:
            run_aggregate.status = event_contract.event_type.value.replace("RUN_", "")
            await self.run_repo.save(run_aggregate)
            
        return await self.event_repo.save(db_event)