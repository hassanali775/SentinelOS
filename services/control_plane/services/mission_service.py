from typing import Mapping, Any
from shared.domain.mission import Mission
from shared.domain.mission_states import MissionStatus
from shared.domain.mission_repository import MissionRepository
from shared.domain.errors import MissionValidationError

class MissionService:
    def __init__(self, repository: MissionRepository):
        """
        Depends strictly on the abstract MissionRepository interface contract.
        Zero exposure to SQLAlchemy AsyncSession or data frameworks.
        """
        self.repository = repository

    async def create_mission(
        self, 
        objective: str, 
        priority: int, 
        metadata: Mapping[str, Any] | None = None
    ) -> Mission:
        """
        Executes the vertical slice use case to validate, instantiate, 
        and persist a canonical Mission aggregate.
        """
        # Refinement 2: Clean up string handling by stripping once up front
        cleaned_objective = objective.strip() if objective else ""
        if not cleaned_objective:
            raise MissionValidationError("Mission objective cannot be empty or blank.")

        # Refinement 3: Enhance debugging by explicitly adding the bad input value
        if priority < 1:
            raise MissionValidationError(f"Mission priority must be greater than or equal to 1. Received priority={priority}")

        # Refinement 1: Default handling for immutable Mapping input type
        safe_metadata = metadata if metadata is not None else {}

        # Rule 4: Mission always initializes in the CREATED lifecycle status
        mission = Mission(
            objective=cleaned_objective,
            priority=priority,
            status=MissionStatus.CREATED,
            metadata=safe_metadata
        )

        # Persist the aggregate through the repository contract boundary
        await self.repository.create(mission)
        
        return mission