"""
SentinelOS — Event Type Registry

This is the canonical list of every event type the system
can produce. Every service — control plane, runtime worker,
replay engine — imports from here.

Adding a new event type requires a deliberate change to this
file, which makes the event taxonomy explicit and auditable.

Event naming convention:
    NOUN_PAST_TENSE or NOUN_ACTION_PAST_TENSE
    Examples: RUN_STARTED, TOOL_CALLED, DECISION_MADE

Grouping:
    Run lifecycle events      → RUN_*
    Planning events           → PLAN_*
    Tool execution events     → TOOL_*
    Agent decision events     → DECISION_*
    Error events              → ERROR_*
    System events             → SYSTEM_*
"""

from enum import StrEnum


class EventType(StrEnum):
    """
    All valid SentinelOS event types.

    StrEnum means the value IS the string:
        EventType.RUN_STARTED == "RUN_STARTED"  → True

    This means event types serialize to JSON cleanly
    without needing .value everywhere.
    """

    # ──────────────────────────────────────────
    # Run Lifecycle
    # ──────────────────────────────────────────

    # A new agent run has been initiated
    RUN_STARTED = "RUN_STARTED"

    # The run completed successfully
    RUN_COMPLETED = "RUN_COMPLETED"

    # The run failed — see payload for error details
    RUN_FAILED = "RUN_FAILED"

    # The run was cancelled by an external request
    RUN_CANCELLED = "RUN_CANCELLED"

    # The run was paused (deterministic checkpoint)
    RUN_PAUSED = "RUN_PAUSED"

    # The run was resumed from a paused state
    RUN_RESUMED = "RUN_RESUMED"

    # ──────────────────────────────────────────
    # Planning Events
    # ──────────────────────────────────────────

    # The agent produced an execution plan
    PLAN_GENERATED = "PLAN_GENERATED"

    # The agent revised its plan mid-execution
    PLAN_REVISED = "PLAN_REVISED"

    # ──────────────────────────────────────────
    # Tool Execution Events
    # ──────────────────────────────────────────

    # The agent invoked a tool
    TOOL_CALLED = "TOOL_CALLED"

    # A tool returned a result
    TOOL_RESULT_RECEIVED = "TOOL_RESULT_RECEIVED"

    # A tool call failed
    TOOL_CALL_FAILED = "TOOL_CALL_FAILED"

    # A tool call exceeded its timeout
    TOOL_CALL_TIMED_OUT = "TOOL_CALL_TIMED_OUT"

    # ──────────────────────────────────────────
    # Agent Decision Events
    # ──────────────────────────────────────────

    # The agent made a reasoning decision
    DECISION_MADE = "DECISION_MADE"

    # The agent reflected on its progress
    REFLECTION_COMPLETED = "REFLECTION_COMPLETED"

    # The agent determined a final answer
    ANSWER_PRODUCED = "ANSWER_PRODUCED"

    # ──────────────────────────────────────────
    # LLM Interaction Events
    # ──────────────────────────────────────────

    # A prompt was sent to the LLM
    LLM_PROMPT_SENT = "LLM_PROMPT_SENT"

    # The LLM returned a response
    LLM_RESPONSE_RECEIVED = "LLM_RESPONSE_RECEIVED"

    # The LLM call failed
    LLM_CALL_FAILED = "LLM_CALL_FAILED"

    # ──────────────────────────────────────────
    # Error Events
    # ──────────────────────────────────────────

    # An unrecoverable error occurred
    ERROR_OCCURRED = "ERROR_OCCURRED"

    # A retryable error occurred
    ERROR_RETRYABLE = "ERROR_RETRYABLE"

    # ──────────────────────────────────────────
    # Replay / System Events
    # ──────────────────────────────────────────

    # A replay was initiated for this run
    REPLAY_INITIATED = "REPLAY_INITIATED"

    # A replay completed successfully
    REPLAY_COMPLETED = "REPLAY_COMPLETED"

    # A snapshot was taken of the run state
    SNAPSHOT_TAKEN = "SNAPSHOT_TAKEN"


# ──────────────────────────────────────────────────────
# Event type groupings — useful for filtering queries
# ──────────────────────────────────────────────────────

RUN_LIFECYCLE_EVENTS: frozenset[EventType] = frozenset({
    EventType.RUN_STARTED,
    EventType.RUN_COMPLETED,
    EventType.RUN_FAILED,
    EventType.RUN_CANCELLED,
    EventType.RUN_PAUSED,
    EventType.RUN_RESUMED,
})

TOOL_EVENTS: frozenset[EventType] = frozenset({
    EventType.TOOL_CALLED,
    EventType.TOOL_RESULT_RECEIVED,
    EventType.TOOL_CALL_FAILED,
    EventType.TOOL_CALL_TIMED_OUT,
})

ERROR_EVENTS: frozenset[EventType] = frozenset({
    EventType.ERROR_OCCURRED,
    EventType.ERROR_RETRYABLE,
    EventType.RUN_FAILED,
    EventType.TOOL_CALL_FAILED,
    EventType.LLM_CALL_FAILED,
})

TERMINAL_EVENTS: frozenset[EventType] = frozenset({
    EventType.RUN_COMPLETED,
    EventType.RUN_FAILED,
    EventType.RUN_CANCELLED,
})
