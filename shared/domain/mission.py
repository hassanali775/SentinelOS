from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Any
from shared.domain.mission_states import MissionStatus


@dataclass(slots=True)
class Mission:
    """

Mission Aggregate Root.

Represents an operator-defined objective.

A Mission owns one or more ExecutionRuns and is responsible
for the business lifecycle of autonomous execution.

This object contains domain behavior only and intentionally
remains independent from persistence and transport layers.

See ADR-001.

    """

    mission_id: UUID = field(default_factory=uuid4)

    objective: str = ""

    status: MissionStatus = MissionStatus.CREATED

    priority: int = 1

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    metadata: dict[str, Any] = field(default_factory=dict)