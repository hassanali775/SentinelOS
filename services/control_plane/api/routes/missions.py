import logging
from fastapi import APIRouter, Depends, HTTPException
from services.control_plane.api.schemas.mission_schemas import MissionCreateRequest, MissionResponse
from services.control_plane.services.mission_service import MissionService
from services.control_plane.api.dependencies import get_mission_service
from shared.domain.errors import MissionValidationError

# Initialize logger using your shared/logging standard
logger = logging.getLogger("sentinel_os.api.missions")

router = APIRouter(prefix="/missions", tags=["Missions"])

@router.post("", response_model=MissionResponse, status_code=201)
async def create_mission(
    request: MissionCreateRequest,
    service: MissionService = Depends(get_mission_service)
):
    """
    Primary API entry point for orchestrating aggregate execution loops.
    """
    try:
        mission = await service.create_mission(
            objective=request.objective,
            priority=request.priority,
            metadata=request.metadata
        )
        
        # Fix: Explicitly instantiate the response schema to prevent domain aggregate leakage
        return MissionResponse(
            mission_id=mission.mission_id,
            objective=mission.objective,
            status=mission.status.value if hasattr(mission.status, 'value') else str(mission.status),
            priority=mission.priority,
            metadata=mission.metadata,
            created_at=mission.created_at
        )
    except MissionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Fix: Added explicit telemetry logging with stack traces before raising internal server exceptions
        logger.exception("Unexpected system failure executing create_mission pipeline.")
        raise HTTPException(status_code=500, detail="Internal system error during instantiation.")