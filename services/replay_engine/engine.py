from uuid import UUID
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from services.event_store.models.agent_event import AgentEventModel
from shared.events.event_types import EventType

class ReconstructedState(BaseModel):
    """The in-memory aggregate view computed dynamically by the Replay Engine."""
    run_id: UUID
    status: str = "PENDING"
    current_sequence: int = 0
    execution_steps: List[Dict[str, Any]] = []
    tools_used: List[str] = []
    last_updated: Optional[datetime] = None

class ReplayEngine:
    @staticmethod
    def reconstruct_state(run_id: UUID, event_stream: List[AgentEventModel]) -> ReconstructedState:
        """
        Pure, deterministic state reducer loop.
        Processes chronological historical events to build the current state.
        """
        state = ReconstructedState(run_id=run_id)
        
        # Sort the stream explicitly by sequence number to guarantee ordered replay
        sorted_stream = sorted(event_stream, key=lambda e: e.sequence_number)
        
        for event in sorted_stream:
            state.current_sequence = event.sequence_number
            state.last_updated = event.timestamp
            
            event_type = event.event_type
            payload = event.payload if isinstance(event.payload, dict) else {}
            
            # Base dictionary matching the expected provider mapping contract
            step_entry = {
                "step": event.sequence_number,
                "action": event_type,
                "payload": payload  # ── CRITICAL FIX: Retain raw payload for LLM parsing ──
            }
            
            # State mutation reduction logic
            if event_type == EventType.RUN_STARTED.value:
                state.status = "RUNNING"
                
            elif event_type == EventType.PLAN_GENERATED.value:
                pass
                
            elif event_type == EventType.TOOL_CALLED.value:
                tool_name = payload.get("tool_name", "unknown_tool")
                if tool_name not in state.tools_used:
                    state.tools_used.append(tool_name)
                
            elif event_type == EventType.TOOL_OUTPUT_RECEIVED.value or event_type == "TOOL_OUTPUT":
                pass
                
            elif event_type == EventType.RUN_COMPLETED.value:
                state.status = "COMPLETED"
                
            elif event_type == EventType.RUN_FAILED.value:
                state.status = "FAILED"
            
            state.execution_steps.append(step_entry)
                
        return state