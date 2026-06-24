import httpx
import logging
from uuid import UUID

logger = logging.getLogger("sentinelos.worker_dispatcher")

class CommandDispatcher:
    """Dispatches background runtime decisions back to the Control Plane API loop."""
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.target_url = f"{base_url}/api/v1/runs"

    async def dispatch_inferred_event(self, run_id: UUID, event_type: str, content: str, sequence_number: int) -> bool:
        """
        Posts a structured inference payload back to the primary event ledger endpoint.
        Forces the system to advance its chronological state machine asynchronously.
        """
        url = f"{self.target_url}/{str(run_id)}/events"
        
        # Build standard contract structure expected by FastAPI schemas
        payload = {
            "run_id": str(run_id),
            "event_type": event_type,
            "sequence_number": sequence_number,  # Pass the calculated incremented index dynamically
            "payload": {
                "execution_summary": content
            },
            "correlation_id": str(run_id)
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 201:
                    logger.info(f"COMMAND_DISPATCH: Success. Broadcasted state advancement event_type={event_type} run_id={run_id}")
                    return True
                else:
                    logger.error(f"COMMAND_DISPATCH: Control Plane rejected command execution status={response.status_code} response={response.text}")
                    return False
            except Exception as e:
                logger.error(f"COMMAND_DISPATCH: Network boundary transmission failure: {str(e)}")
                return False