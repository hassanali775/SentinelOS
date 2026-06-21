from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from services.event_store.repositories.base import AbstractRepository
from services.event_store.models.agent_event import AgentEventModel

class PostgresEventRepository(AbstractRepository[AgentEventModel]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[AgentEventModel]:
        result = await self.session.execute(
            select(AgentEventModel).where(AgentEventModel.event_id == id)
        )
        return result.scalar_one_or_none()

    async def save(self, entity: AgentEventModel) -> AgentEventModel:
        """Appends a new immutable fact ledger record directly to the stream."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get_stream_by_run_id(self, run_id: UUID) -> List[AgentEventModel]:
        """
        CRITICAL CORE QUERY: Reclaims the absolute sequence history of an agent run,
        guaranteeing chronological sorting order for deterministic state replay.
        """
        result = await self.session.execute(
            select(AgentEventModel)
            .where(AgentEventModel.run_id == run_id)
            .order_by(AgentEventModel.sequence_number.asc())
        )
        return list(result.scalars().all())