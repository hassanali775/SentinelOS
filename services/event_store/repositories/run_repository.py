from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from services.event_store.repositories.base import AbstractRepository
from services.event_store.models.agent_run import AgentRunModel

class PostgresRunRepository(AbstractRepository[AgentRunModel]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[AgentRunModel]:
        """Fetch a specific agent run state directly by its unique identity."""
        result = await self.session.execute(
            select(AgentRunModel).where(AgentRunModel.run_id == id)
        )
        return result.scalar_one_or_none()

    async def save(self, entity: AgentRunModel) -> AgentRunModel:
        """Saves or updates the AgentRun tracking model using OCC version guards."""
        # Check if this aggregate root already exists in our tracking session
        existing = await self.get_by_id(entity.run_id)
        
        if not existing:
            self.session.add(entity)
        else:
            # Enforce Optimistic Concurrency Control (OCC)
            # If the version in memory doesn't match what's expected, abort transaction
            if existing.version != entity.version:
                raise RuntimeError(
                    f"Concurrency Conflict: Aggregate state out of sync. "
                    f"Expected version {entity.version}, found {existing.version}."
                )
            # Increment version tracking dynamically before pushing down stream
            entity.version += 1
            await self.session.merge(entity)
            
        await self.session.flush()
        return entity