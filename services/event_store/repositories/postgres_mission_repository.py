from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from shared.domain.mission import Mission
from shared.domain.mission_states import MissionStatus
from shared.domain.mission_repository import MissionRepository
from services.event_store.models.mission import MissionModel

class PostgresMissionRepository(MissionRepository):
    """
    PostgreSQL implementation of the MissionRepository contract.
    Handles persistence and state rehydration using AsyncSQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _load_model(self, mission_id: UUID) -> Optional[MissionModel]:
        """Private helper to minimize query duplication across methods."""
        result = await self.session.execute(
            select(MissionModel).where(MissionModel.mission_id == mission_id)
        )
        return result.scalar_one_or_none()

    async def save(self, mission: Mission) -> Mission:
        """
        Main interface method satisfying the abstract contract.
        Routes to explicit create or update paths based on existence.
        """
        db_model = await self._load_model(mission.mission_id)
        if not db_model:
            await self.create(mission)
        else:
            await self.update(mission)
        return mission

    async def create(self, mission: Mission) -> Mission:
        """Explicit insert path for new Mission aggregates."""
        db_model = MissionModel(
            mission_id=mission.mission_id,
            objective=mission.objective,
            status=mission.status.value,  # Fixed Issue 3: No guessing, direct enum access
            priority=mission.priority,
            metadata_json=mission.metadata  # Fixed Issue 2: Maps domain 'metadata' to DB 'metadata_json'
        )
        self.session.add(db_model)
        return mission

    async def update(self, mission: Mission) -> Mission:
        """Explicit update path for existing modified Mission aggregates."""
        db_model = await self._load_model(mission.mission_id)
        if not db_model:
            raise ValueError(f"Cannot update non-existent mission: {mission.mission_id}")
            
        db_model.objective = mission.objective
        db_model.status = mission.status.value
        db_model.priority = mission.priority
        db_model.metadata_json = mission.metadata  # Maps safely
        return mission

    async def get(self, mission_id: UUID) -> Optional[Mission]:
        """Retrieve a Mission record and rehydrate it into a pure Domain Object."""
        db_model = await self._load_model(mission_id)
        if not db_model:
            return None
            
        # Fixed Issue 1: Ensures domain owns the type using MissionStatus wrapper
        return Mission(
            mission_id=db_model.mission_id,
            objective=db_model.objective,
            status=MissionStatus(db_model.status),
            priority=db_model.priority,
            metadata=db_model.metadata_json  # Maps safely back to domain 'metadata'
        )