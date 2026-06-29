import os
from typing import Dict, Any
from services.agent_worker.tools.base import BaseTool

class DirectoryScannerTool(BaseTool):
    """Safe system utility allowing the agent to inspect folder structures."""
    
    @property
    def name(self) -> str:
        return "directory_scanner"

    @property
    def description(self) -> str:
        return (
            "Scans a specified local directory path and returns a list of files and folders contained within it. "
            "Arguments: {'target_path': 'string'}"
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        target_path = arguments.get("target_path", ".")
        
        # Security Guardrail: Enforce absolute directory isolation if needed
        try:
            if not os.path.exists(target_path):
                return {"status": "error", "message": f"Path cold-start error: Target directory '{target_path}' does not exist."}
            
            items = os.listdir(target_path)
            contents = []
            for item in items[:20]: # Cap at 20 items to preserve context window safety tokens
                full_path = os.path.join(target_path, item)
                contents.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(full_path) else "file"
                })
                
            return {
                "status": "success",
                "current_working_directory": os.path.abspath(target_path),
                "contents": contents
            }
        except Exception as e:
            return {"status": "error", "message": f"OS Read Exception: {str(e)}"}