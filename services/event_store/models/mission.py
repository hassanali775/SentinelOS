from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from services.event_store.database import Base
from shared.domain.mission_states import MissionStatus


class MissionModel(Base):
    """
    SQLAlchemy persistence model for Mission.

    This model is responsible only for database persistence.
    It is intentionally separate from the Mission domain object.
    """

    __tablename__ = "missions"

    mission_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    objective: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=MissionStatus.CREATED.value,
        nullable=False,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )