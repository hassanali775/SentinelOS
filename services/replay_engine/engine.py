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
        # Initialize an empty state object for this specific run context
        state = ReconstructedState(run_id=run_id)
        
        for event in event_stream:
            state.current_sequence = event.sequence_number
            state.last_updated = event.timestamp
            
            # Match the raw string event type to our system boundaries
            event_type = event.event_type
            payload = event.payload or {}
            
            # State mutation reduction logic
            if event_type == EventType.RUN_STARTED.value:
                state.status = "RUNNING"
                state.execution_steps.append({
                    "step": event.sequence_number,
                    "action": "Lifecycle initialization completed."
                })
                
            elif event_type == EventType.PLAN_GENERATED.value:
                state.execution_steps.append({
                    "step": event.sequence_number,
                    "action": f"LLM Plan Formulated: {payload.get('plan', '')}"
                })
                
            elif event_type == EventType.TOOL_CALLED.value:
                tool_name = payload.get("tool_name", "unknown_tool")
                state.tools_used.append(tool_name)
                state.execution_steps.append({
                    "step": event.sequence_number,
                    "action": f"Invoked infrastructure tool component: [{tool_name}]"
                })
                
            elif event_type == EventType.TOOL_OUTPUT_RECEIVED.value:
                state.execution_steps.append({
                    "step": event.sequence_number,
                    "action": f"Captured execution outcome: {payload.get('output', '')}"
                })
                
            elif event_type == EventType.RUN_COMPLETED.value:
                state.status = "COMPLETED"
                state.execution_steps.append({
                    "step": event.sequence_number,
                    "action": "Lifecycle execution reached terminal success state."
                })
                
            elif event_type == EventType.RUN_FAILED.value:
                state.status = "FAILED"
                state.execution_steps.append({
                    "step": event.sequence_number,
                    "action": f"Fatal execution exception captured: {payload.get('error', 'Unknown application error')}"
                })
                
        return state