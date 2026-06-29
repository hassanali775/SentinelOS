from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """Abstract base class enforcing strict interface contracts for local system execution."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The canonical name used by the LLM to invoke this tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed functional description to inject into the model's system context window."""
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the specific OS-level automation logic safely."""
        pass