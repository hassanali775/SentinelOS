from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Dict, Any
from services.event_store.database import get_db_session
from services.event_store.repositories.event_repository import PostgresEventRepository
from services.replay_engine.engine import ReplayEngine, ReconstructedState
from services.control_plane.services.event_service import EventService
from shared.contracts.base_event import BaseEvent

router = APIRouter(prefix="/api/v1/runs/{run_id}", tags=["Agent Events & Replay"])

@router.post("/events", status_code=status.HTTP_201_CREATED)
async def append_event_to_run_stream(
    run_id: UUID,
    event_contract: BaseEvent,
    db: AsyncSession = Depends(get_db_session)
):
    """Appends an execution event to the agent's immutable history ledger."""
    if run_id != event_contract.run_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path parameter mismatch: URL run_id must match body payload tracking attributes."
        )
    try:
        service = EventService(db)
        inserted_row = await service.append_event_to_stream(event_contract)
        return {"status": "SUCCESS", "sequence_assigned": inserted_row.sequence_number}
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/timeline", response_model=ReconstructedState)
async def get_reconstructed_run_timeline(
    run_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Triggers the Replay Engine dynamically to reconstruct the current 
    in-memory state of an execution path from historical facts.
    """
    repo = PostgresEventRepository(db)
    stream = await repo.get_stream_by_run_id(run_id)
    
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No event stream history found for the target run identifier: {run_id}"
        )
        
    # Run the stream through our deterministic engine layer
    state = ReplayEngine.reconstruct_state(run_id, stream)
    return state