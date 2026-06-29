from abc import ABC, abstractmethod

from shared.domain.mission import Mission
from uuid import UUID
from typing import Optional

class MissionRepository(ABC):
    """
    Domain contract for Mission persistence.

    Infrastructure implementations (Postgres, SQLite,
    in-memory, etc.) must satisfy this interface.
    """

    @abstractmethod
    async def save(
    self,
    mission: Mission,
) -> Mission:
        """
        Persist a Mission aggregate.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        mission_id: UUID,
    ) -> Optional[Mission]:
        """
        Retrieve a Mission aggregate.
        """
        raise NotImplementedError