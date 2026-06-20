"""Evaluation model — AI assessment of student diagnosis."""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.dependencies import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), unique=True, nullable=False
    )

    # Student submission
    primary_diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    differential: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_tests: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI evaluation results
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    consultation_score: Mapped[float] = mapped_column(Float, nullable=False)
    diagnosis_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    teacher_comment: Mapped[str] = mapped_column(Text, nullable=False)
    standard_diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    history_summary: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="evaluation")
