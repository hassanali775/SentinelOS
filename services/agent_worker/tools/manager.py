import logging
from typing import Dict, Any, Optional
from services.agent_worker.tools.base import BaseTool
from services.agent_worker.tools.directory_scanner import DirectoryScannerTool

logger = logging.getLogger("sentinelos.tool_manager")

class ToolManager:
    """Centralized production-grade secure sandbox boundary for agent automation execution."""
    
    def __init__(self):
        self._registry: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Statically maps available native OS tooling primitives on initialization."""
        # Add the directory scanner tool to our active infrastructure map
        scanner = DirectoryScannerTool()
        self._registry[scanner.name] = scanner
        logger.info(f"TOOL_REGISTRY: Loaded capability node successfully. tool_name='{scanner.name}'")

    def get_tool_definitions_context(self) -> str:
        """
        Compiles structural descriptions of all loaded tools.
        Injected directly into the system prompt to let the model know its active capabilities.
        """
        context_string = "AVAILABLE AUTOMATION TOOLS:\n"
        for tool in self._registry.values():
            context_string += f"- Name: {tool.name}\n  Description: {tool.description}\n\n"
        return context_string

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely intercepts and evaluates an incoming LLM tool call request.
        Wraps processing inside boundary walls to protect the underlying host worker thread.
        """
        tool: Optional[BaseTool] = self._registry.get(tool_name)
        
        if not tool:
            logger.warning(f"TOOL_REGISTRY: Malformed execution intercept. Unrecognized tool signature -> name='{tool_name}'")
            return {
                "status": "error",
                "message": f"Execution Registry Rejection: Tool '{tool_name}' is not registered within this cluster profile."
            }

        logger.info(f"TOOL_EXECUTE: Invoking system transaction. tool_name='{tool_name}' arguments={arguments}")
        
        try:
            # Execute the isolated asynchronous task boundary
            result = await tool.execute(arguments)
            return result
        except Exception as e:
            logger.error(f"TOOL_EXECUTE: Runtime explosion caught during isolation loop -> tool_name='{tool_name}' error={str(e)}")
            return {
                "status": "error",
                "message": f"Runtime Fatal Trace Exception: {str(e)}"
            }