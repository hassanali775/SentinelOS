from enum import Enum

class MissionStatus(str, Enum):
    """
    Canonical State Machine governing the SentinelOS Mission runtime domain.
    """
    # Standard Lifecycle Progression Flow
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    PLANNED = "PLANNED"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    VALIDATING = "VALIDATING"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"

    # Alternative Terminal States
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    TIMEOUT = "TIMEOUT"

    # Add this directly to the bottom of shared/domain/mission_states.py

def map_legacy_run_status(legacy_status: str) -> MissionStatus:
    """
    Translates legacy AgentRunModel states to the new canonical MissionStatus.
    Ensures backward compatibility during the Sprint 2 domain evolution.
    """
    mapping = {
        "PENDING": MissionStatus.CREATED,
        "RUNNING": MissionStatus.EXECUTING,
        "SUCCESS": MissionStatus.COMPLETED,
        "FAILED": MissionStatus.FAILED
    }
    return mapping.get(legacy_status.upper(), MissionStatus.FAILED)