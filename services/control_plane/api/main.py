import os
import sys
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from services.control_plane.api.routes import runs, events
from services.control_plane.api.routes.missions import router as missions_router

app = FastAPI(
    title="SentinelOS Control Plane",
    description="Event-Sourced Enterprise Agent Orchestration Layer",
    version="0.1.0"
)

# Mount our custom modular system route tables
app.include_router(runs.router)
app.include_router(events.router)
app.include_router(missions_router, prefix="/api/v1")

@app.get("/api/v1/runs/{run_id}/stream", tags=["Telemetry"])
async def stream_run_events(run_id: str):
    """
    Exposes a live SSE endpoint that streams runtime events straight to the UI canvas.
    """
    async def event_generator():
        sent_event_ids = set()
        
        while True:
            try:
                # Plugs directly into the existing endpoint engine logic from your routes
                # We reuse the active router logic to fetch the event list seamlessly
                events_response = await events.get_run_events(run_id)
            except Exception as e:
                yield f"data: {{\"error\": \"Telemetry stream connection stalled: {str(e)}\"}}\n\n"
                await asyncio.sleep(1)
                continue

            for event in events_response:
                # Unique key constraint using database ID or slot sequence number
                event_key = getattr(event, "id", str(getattr(event, "sequence_number", "")))
                if event_key not in sent_event_ids:
                    # Handle both Pydantic schemas and dictionary objects gracefully
                    event_json = event.model_dump_json() if hasattr(event, "model_dump_json") else str(event)
                    yield f"data: {event_json}\n\n"
                    sent_event_ids.add(event_key)
            
            # Auto-disconnect if the agent signals a terminal exit condition
            is_terminal = any(getattr(e, "event_type", "") in ["RUN_COMPLETED", "RUN_FAILED"] for e in events_response)
            if is_terminal:
                yield "data: {\"status\": \"STREAM_COMPLETE\"}\n\n"
                break
                
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/v1/health", tags=["System Utility"])
async def system_health_check():
    """Liveness probe for checking basic control plane engine runtime status."""
    return {
        "status": "GREEN",
        "subsystems": {
            "control_plane": "ONLINE"
        }
    }

if __name__ == "__main__":
    import uvicorn

    # Dynamically inject the project root to ensure standard python imports resolve
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Boot Uvicorn by explicitly telling the reloader to watch the root directory
    uvicorn.run(
        "services.control_plane.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=[project_root]
    )