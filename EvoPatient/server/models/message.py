"""Message model — one per doctor question or patient answer."""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.dependencies import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # "doctor" or "patient"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Patient messages only: quality scores
    score_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_relevance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_faithfulness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_robustness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmed_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="messages")
