from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from uuid import UUID

T = TypeVar("T")

class AbstractRepository(ABC, Generic[T]):
    """The strict domain boundary contract for all data access layers."""
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[T]:
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        pass