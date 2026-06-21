from datetime import datetime
from uuid import UUID, uuid4
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from shared.events.event_types import EventType

class BaseEvent(BaseModel):
    """The immutable enterprise event contract specification schema."""
    event_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    event_type: EventType
    sequence_number: int = Field(..., ge=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID
    causation_id: Optional[UUID] = None
    schema_version: int = 1

    model_config = {
        "frozen": True,  # Ensures the event instance data is structurally immutable
        "populate_by_name": True
    }