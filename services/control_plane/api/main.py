from fastapi import FastAPI
from services.control_plane.api.routes import runs

app = FastAPI(
    title="SentinelOS Control Plane",
    description="Event-Sourced Enterprise Agent Orchestration Layer",
    version="0.1.0"
)

# Mount our custom modular system route tables
app.include_router(runs.router)

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
    import os
    import sys

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