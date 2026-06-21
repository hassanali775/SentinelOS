from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any

class RunCreateRequest(BaseModel):
    """Payload template validated at entry for spawning a new execution path."""
    agent_id: UUID
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class RunResponse(BaseModel):
    """Production-grade tracking structure returned back to the client routing tier."""
    run_id: UUID
    agent_id: UUID
    status: str
    version: int
    metadata_json: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allows Pydantic to read SQLAlchemy ORM models directly