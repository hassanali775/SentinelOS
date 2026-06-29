from enum import Enum


class ExecutionStatus(str, Enum):
    """
Execution lifecycle for a single ExecutionRun.

This enum represents the state of one execution attempt only.
It must never be reused for Mission lifecycle management.

See ADR-001.
"""

    PENDING = "PENDING"

    STARTING = "STARTING"

    RUNNING = "RUNNING"

    TOOL_EXECUTION = "TOOL_EXECUTION"

    STREAMING = "STREAMING"

    VALIDATING = "VALIDATING"

    COMPLETED = "COMPLETED"

    FAILED = "FAILED"

    CANCELLED = "CANCELLED"