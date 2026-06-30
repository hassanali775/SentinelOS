import logging
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.event_store.database import get_db_session 
from shared.domain.mission_repository import MissionRepository # Fix: Import the domain abstraction interface
from services.event_store.repositories.postgres_mission_repository import PostgresMissionRepository
from services.control_plane.services.mission_service import MissionService

# Fix: Type hint returns the domain interface contract instead of Postgres implementation
async def get_mission_repository(session: AsyncSession = Depends(get_db_session)) -> MissionRepository:
    """Provides an abstract Mission repository interface contract boundary."""
    return PostgresMissionRepository(session)

async def get_mission_service(repository: MissionRepository = Depends(get_mission_repository)) -> MissionService:
    """Provides a validated Mission application service layer instance."""
    return MissionService(repository)