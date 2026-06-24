import httpx
import logging
import json
from typing import Dict, Any, List

logger = logging.getLogger("sentinelos.ollama")

class OllamaProvider:
    """Asynchronous provider interface for handling local LLM inference chains."""
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3"):
        self.base_url = f"{base_url}/api/chat"
        self.model_name = model_name

    async def generate_reasoning_step(self, history_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sends the current reconstructed event timeline to the local LLM.
        Instructs the model to output a structured JSON response detailing its next operational action.
        """
        system_prompt = (
            "You are the autonomous execution engine of SentinelOS. "
            "Analyze the chronological history of events provided and determine the next logical action. "
            "You must respond with a valid, raw JSON object matching this structure exactly:\n"
            "{\n"
            '  "action_type": "PLAN_GENERATED" | "TOOL_CALLED" | "RUN_COMPLETED",\n'
            '  "content": "Description of the plan or the core tool payload text"\n'
            "}\n"
            "Do not include markdown blocks, code wrappers, or conversational prose. Return only raw JSON."
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        # Format our reconstructed ledger timeline back into the conversational context window
        for step in history_steps:
            messages.append({
                "role": "user", 
                "content": f"Sequence {step.get('step')}: Action taken was -> {step.get('action')}"
            })

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": "json" # Forces Ollama to constrain vocabulary logits to valid JSON schemas
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                
                result_json = response.json()
                message_content = result_json.get("message", {}).get("content", "{}")
                
                # ── EXPLICIT DEBUG LOG ──
                logger.info(f"RAW MODEL OUTPUT TARGET RECEIVED: '{message_content}'")
                
                parsed_data = json.loads(message_content)
                
                # ── RESILIENT NORMALIZATION LAYER ──
                # Defensive keys evaluation guarantees smaller models conform to what the worker needs
                normalized_decision = {}
                
                # Extract action type regardless of exact key casing or naming drift
                action = parsed_data.get("action_type") or parsed_data.get("action") or "PLAN_GENERATED"
                if action not in ["PLAN_GENERATED", "TOOL_CALLED", "RUN_COMPLETED"]:
                    action = "PLAN_GENERATED"
                
                normalized_decision["action_type"] = action
                normalized_decision["content"] = parsed_data.get("content") or parsed_data.get("description") or parsed_data.get("text") or "Autonomous decision step executed by local model."
                
                return normalized_decision
                
            except httpx.HTTPStatusError as http_err:
                logger.error(f"Ollama network boundary transaction rejected: {http_err.response.text}")
                raise
            except Exception as e:
                logger.error(f"Failed to decode local reasoning model token structure: {str(e)}")
                return {"action_type": "RUN_FAILED", "content": f"Inference pipeline error: {str(e)}"}