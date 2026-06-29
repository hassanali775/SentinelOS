from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import Any, Dict

class EventEnvelope(BaseModel):
    """
    Universal metadata wrap for all domain-driven events within SentinelOS.
    Implements standard patterns for event sourcing and asynchronous tracking.
    """
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    mission_id: UUID
    execution_id: UUID
    correlation_id: UUID
    causation_id: UUID | None = None
    sequence_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    schema_version: int = 1
    payload: Dict[str, Any]

    class Config:
        frozen = True  # Enforces structural immutability post-instantiation