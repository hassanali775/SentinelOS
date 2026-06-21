from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from services.event_store.database import get_db_session
from services.control_plane.services.run_service import RunService
from services.control_plane.api.schemas.run_schemas import RunCreateRequest, RunResponse

router = APIRouter(prefix="/api/v1/runs", tags=["Agent Runs"])

@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_run(
    payload: RunCreateRequest, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Spawns an isolated Agent Run lifecycle context boundary.
    Saves the aggregate tracker and appends the initial RUN_STARTED state.
    """
    try:
        service = RunService(db)
        run_aggregate = await service.create_new_run(
            agent_id=payload.agent_id, 
            metadata=payload.metadata
        )
        return run_aggregate
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize core agent execution track: {str(e)}"
        )