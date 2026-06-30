from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Mapping, Any

class MissionCreateRequest(BaseModel):
    objective: str = Field(..., max_length=512, description="The core business objective for the autonomous mission.")
    priority: int = Field(default=1, ge=1, description="Scheduling priority tier.")
    metadata: Mapping[str, Any] = Field(default_factory=dict, description="Arbitrary execution context parameters.")

class MissionResponse(BaseModel):
    mission_id: UUID
    objective: str
    status: str
    priority: int
    metadata: Mapping[str, Any]
    created_at: datetime  # Fix: Added explicit created_at timestamp

    class Config:
        from_attributes = True