"""
SentinelOS — Canonical Event Contract

This is the single source of truth for what an event looks like.
Every service reads this. No service invents its own event shape.

The BaseEvent is an immutable value object. Once created, its
fields cannot be changed. This enforces the Event Sourcing
guarantee: events describe facts that already happened.

Design decisions:
    - UUID v4 for event_id and run_id (globally unique, unguessable)
    - ULID for sequence ordering (sortable by time + unique)
    - datetime in UTC always — no timezone ambiguity
    - payload is a free-form dict — each event type has its
      own payload schema validated separately
    - schema_version enables future event upcasting
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from shared.events.event_types import EventType


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime. Never use datetime.utcnow()."""
    return datetime.now(UTC)


class BaseEvent(BaseModel):
    """
    Canonical event shape for all SentinelOS events.

    Fields:
        event_id:       Unique identity of this specific event.
                        Generated at creation, never reused.

        run_id:         The agent run this event belongs to.
                        All events in a run share this ID.

        event_type:     What happened. Always from the EventType enum.

        sequence_number: Position of this event within the run.
                        Used for ordered replay. Must be monotonically
                        increasing per run_id.

        timestamp:      Wall clock time the event occurred (UTC).
                        Used for human-readable timelines.

        payload:        Event-specific data. Structure varies by
                        event_type. Validated downstream.

        correlation_id: Traces a single user-initiated operation
                        across all events it produces, even across
                        service boundaries.
                        "What request triggered all of this?"

        causation_id:   The event_id of the event that directly
                        caused this event. Builds the causal chain.
                        "Which specific event caused this one?"
                        Null for the first event in a chain.

        schema_version: Version of the payload schema.
                        Enables upcasting when payload format changes.
                        Always 1 for new events.

        published_at:   Set when the event is published to Redpanda.
                        Null until published. Allows detection of
                        events that failed to publish.
    """

    model_config = {"frozen": True}  # Immutable after creation

    event_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    event_type: EventType
    sequence_number: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=_utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: UUID | None = Field(default=None)
    schema_version: int = Field(default=1, ge=1)
    published_at: datetime | None = Field(default=None)

    @field_validator("timestamp", "published_at", mode="before")
    @classmethod
    def ensure_utc(cls, v: datetime | None) -> datetime | None:
        """Ensure all datetimes are timezone-aware UTC."""
        if v is None:
            return None
        if isinstance(v, datetime):
            if v.tzinfo is None:
                # Assume naive datetimes are UTC (common from DB drivers)
                return v.replace(tzinfo=UTC)
            return v.astimezone(UTC)
        return v

    @field_validator("sequence_number")
    @classmethod
    def sequence_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("sequence_number must be >= 0")
        return v

    def to_kafka_payload(self) -> dict[str, Any]:
        """
        Serialize for publishing to Redpanda.

        Converts UUIDs to strings and datetimes to ISO strings
        because Kafka messages are byte strings, not Python objects.
        """
        return {
            "event_id": str(self.event_id),
            "run_id": str(self.run_id),
            "event_type": self.event_type,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "correlation_id": str(self.correlation_id),
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_kafka_payload(cls, data: dict[str, Any]) -> "BaseEvent":
        """
        Deserialize from a Redpanda message.

        Converts string UUIDs and ISO datetime strings back
        to their proper Python types.
        """
        return cls(
            event_id=UUID(data["event_id"]),
            run_id=UUID(data["run_id"]),
            event_type=EventType(data["event_type"]),
            sequence_number=data["sequence_number"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            payload=data.get("payload", {}),
            correlation_id=UUID(data["correlation_id"]),
            causation_id=UUID(data["causation_id"]) if data.get("causation_id") else None,
            schema_version=data.get("schema_version", 1),
        )

    def __repr__(self) -> str:
        return (
            f"BaseEvent("
            f"type={self.event_type}, "
            f"run_id={str(self.run_id)[:8]}..., "
            f"seq={self.sequence_number}"
            f")"
        )
