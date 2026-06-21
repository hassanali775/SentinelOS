from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Integer, DateTime, JSON, UniqueConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from services.event_store.database import Base

class AgentEventModel(Base):
    __tablename__ = "agent_events"

    event_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("agent_runs".run_id, ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(nullable=False)
    causation_id: Mapped[UUID] = mapped_column(nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        # Enforce strict append-only ordering at the database engine level
        UniqueConstraint("run_id", "sequence_number", name="uq_run_sequence"),
        # Optimize performance for the most common query: "Fetch all events for run X sorted by sequence"
        Index("idx_run_sequence", "run_id", "sequence_number"),
    )