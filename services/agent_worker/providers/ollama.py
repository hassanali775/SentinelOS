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

    async def generate_reasoning_step(self, history_steps: List[Dict[str, Any]], tools_context: str) -> Dict[str, Any]:
        """
        Sends the current reconstructed event timeline and available tools schema to the local LLM.
        Instructs the model to output a structured JSON response detailing its next operational action.
        """
        system_prompt = (
            "You are the autonomous execution engine of SentinelOS.\n\n"
            "Analyze the chronological history of events provided and determine the next logical action. "
            "You have access to local OS automation utilities. If you need information from the system to "
            "progress, choose TOOL_CALLED and provide the tool name and precise arguments.\n\n"
            f"{tools_context}\n"
            "You must respond with a valid, raw JSON object matching this structure exactly:\n"
            "{\n"
            '  "action_type": "PLAN_GENERATED" | "TOOL_CALLED" | "RUN_COMPLETED",\n'
            '  "content": "A high-level description of your current execution intent or rationale.",\n'
            '  "tool_name": "string or null (Only populate if action_type is TOOL_CALLED)",\n'
            '  "arguments": { "key": "value" } or null (Only populate if action_type is TOOL_CALLED)\n'
            "}\n"
            "Do not include markdown blocks, code wrappers, or conversational prose. Return only raw JSON."
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        # Extract task objective first to put it in context as a persistent anchor
        task_instruction = None
        for step in history_steps:
            if step.get('action') == "RUN_STARTED":
                payload = step.get('payload') or {}
                task_instruction = (
                    payload.get("metadata", {}).get("task") or 
                    payload.get("task") or
                    payload.get("execution_summary") # Fallback safety for wrapped payloads
                )
                break

        if task_instruction:
            messages.append({
                "role": "user",
                "content": f"CRITICAL RUN TASK OBJECTIVE: {task_instruction}"
            })

        # Append chronological event histories cleanly
        for step in history_steps:
            action_text = step.get('action', '')
            payload = step.get('payload') or {}
            summary = payload.get("execution_summary") or payload.get("output") or payload.get("plan") or ""
            
            content_str = f"Step {step.get('step')} [{action_text}]"
            if summary:
                content_str += f" - Status Detail: {summary}"

            messages.append({
                "role": "user", 
                "content": content_str
            })

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": "json"
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                
                result_json = response.json()
                message_content = result_json.get("message", {}).get("content", "{}")
                
                logger.info(f"RAW MODEL OUTPUT TARGET RECEIVED: '{message_content}'")
                parsed_data = json.loads(message_content)
                
                normalized_decision = {}
                action = parsed_data.get("action_type") or parsed_data.get("action") or "PLAN_GENERATED"
                if action not in ["PLAN_GENERATED", "TOOL_CALLED", "RUN_COMPLETED"]:
                    action = "PLAN_GENERATED"
                
                normalized_decision["action_type"] = action
                normalized_decision["content"] = parsed_data.get("content") or parsed_data.get("description") or "Step executed by local model."
                normalized_decision["tool_name"] = parsed_data.get("tool_name")
                normalized_decision["arguments"] = parsed_data.get("arguments") or {}
                
                return normalized_decision
                
            except httpx.HTTPStatusError as http_err:
                logger.error(f"Ollama network boundary transaction rejected: {http_err.response.text}")
                raise
            except Exception as e:
                logger.error(f"Failed to decode local reasoning model token structure: {str(e)}")
                return {"action_type": "RUN_FAILED", "content": f"Inference pipeline error: {str(e)}"}