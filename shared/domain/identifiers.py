from typing import NewType
from uuid import UUID

MissionId = NewType("MissionId", UUID)
ExecutionId = NewType("ExecutionId", UUID)
CorrelationId = NewType("CorrelationId", UUID)