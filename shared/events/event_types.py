from enum import Enum

class EventType(str, Enum):
    # Core lifecycle states
    RUN_STARTED = "RUN_STARTED"
    PLAN_GENERATED = "PLAN_GENERATED"
    
    # Execution states
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_OUTPUT_RECEIVED = "TOOL_OUTPUT_RECEIVED"
    
    # Final terminal states
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"