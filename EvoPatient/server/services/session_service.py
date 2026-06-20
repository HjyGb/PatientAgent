"""Session service — manages consultation session lifecycle with DB persistence.

Replaces the in-memory _session_registry in case_service.py with proper DB-backed
session tracking, while keeping the simulateflow SessionContext in memory for live
agent access.
"""

import uuid
from datetime import datetime

from sqlalchemy import select, update, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession as DbAsyncSession

from server.models.session import Session
from server.models.message import Message
from server.models.evaluation import Evaluation


class SessionService:
    """Creates, retrieves, and manages consultation sessions in the database."""

    # In-memory registry: session_id (UUID str) → simulateflow SessionContext
    _context_registry: dict[str, object] = {}

    # ═══════════════════════════════════════════════════════════════
    # In-memory context management (for live agent access)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def register_context(cls, session_id: str, ctx: object) -> None:
        """Store the simulateflow SessionContext for agent lookups."""
        cls._context_registry[session_id] = ctx

    @classmethod
    def get_context(cls, session_id: str):
        """Retrieve simulateflow SessionContext by session ID."""
        if session_id not in cls._context_registry:
            raise KeyError(f"Session {session_id} not found")
        return cls._context_registry[session_id]

    @classmethod
    def get_patient_agent(cls, session_id: str):
        """Retrieve the Patient agent from a session's context."""
        ctx = cls._context_registry.get(session_id)
        if ctx is None:
            return None
        return ctx.patient

    # ═══════════════════════════════════════════════════════════════
    # DB operations
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    async def create_session(
        cls,
        db: DbAsyncSession,
        *,
        case_row: int,
        sheet_name: str = "Sheet1",
        department: str = "内科",
        chief_complaint: str = "",
        user_id: str | None = None,
        max_turns: int = 12,
    ) -> Session:
        """Create a new consultation session record in the database.

        Returns the committed Session ORM object. The session.id is a UUID
        that becomes the API-level session identifier.
        """
        sid = str(uuid.uuid4())
        session = Session(
            id=sid,
            user_id=user_id or "00000000-0000-0000-0000-000000000000",
            case_row=case_row,
            sheet_name=sheet_name,
            department=department,
            chief_complaint=chief_complaint,
            status="active",
            turn_count=0,
            max_turns=max_turns,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @classmethod
    async def get_session(
        cls, db: DbAsyncSession, session_id: str
    ) -> Session | None:
        """Retrieve a session by ID."""
        result = await db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    @classmethod
    async def end_session(
        cls, db: DbAsyncSession, session_id: str, status: str = "ended"
    ) -> bool:
        """Mark a session as ended (or diagnosed / evaluated)."""
        session = await cls.get_session(db, session_id)
        if session is None:
            return False
        session.status = status
        session.ended_at = datetime.utcnow()
        await db.commit()
        return True

    @classmethod
    async def increment_turn(cls, db: DbAsyncSession, session_id: str) -> int:
        """Atomically increment the turn counter. Returns new turn count."""
        await db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(turn_count=Session.turn_count + 1)
        )
        await db.commit()
        session = await cls.get_session(db, session_id)
        return session.turn_count if session else 0

    # ═══════════════════════════════════════════════════════════════
    # Messages
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    async def save_message(
        cls,
        db: DbAsyncSession,
        *,
        session_id: str,
        role: str,
        content: str,
        turn_number: int,
        score_overall: int | None = None,
        score_relevance: int | None = None,
        score_faithfulness: int | None = None,
        score_robustness: int | None = None,
        confirmed_info: dict | None = None,
    ) -> Message:
        """Persist a chat message (doctor question or patient answer)."""
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            turn_number=turn_number,
            score_overall=score_overall,
            score_relevance=score_relevance,
            score_faithfulness=score_faithfulness,
            score_robustness=score_robustness,
            confirmed_info=confirmed_info,
        )
        db.add(message)
        await db.commit()
        return message

    @classmethod
    async def get_messages(
        cls, db: DbAsyncSession, session_id: str
    ) -> list[Message]:
        """Retrieve all messages for a session, ordered by creation time."""
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())

    @classmethod
    async def get_session_history(
        cls,
        db: DbAsyncSession,
        session_id: str,
    ) -> list[dict]:
        """Return all messages for a session as simple dicts (for API)."""
        messages = await cls.get_messages(db, session_id)
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "turn_number": m.turn_number,
                "scores": (
                    {
                        "overall": m.score_overall,
                        "relevance": m.score_relevance,
                        "faithfulness": m.score_faithfulness,
                        "robustness": m.score_robustness,
                    }
                    if m.role == "patient"
                    else None
                ),
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in messages
        ]

    # ═══════════════════════════════════════════════════════════════
    # Evaluations
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    async def save_evaluation(
        cls,
        db: DbAsyncSession,
        *,
        session_id: str,
        primary_diagnosis: str,
        evidence: str = "",
        differential: str = "",
        suggested_tests: str = "",
        overall_score: float = 3.0,
        consultation_score: float = 3.0,
        diagnosis_score: float = 3.0,
        dimension_scores: dict | None = None,
        teacher_comment: str = "",
        standard_diagnosis: str = "",
        history_summary: dict | None = None,
    ) -> Evaluation:
        """Persist an evaluation and mark session as evaluated."""
        evaluation = Evaluation(
            id=str(uuid.uuid4()),
            session_id=session_id,
            primary_diagnosis=primary_diagnosis,
            evidence=evidence,
            differential=differential,
            suggested_tests=suggested_tests,
            overall_score=overall_score,
            consultation_score=consultation_score,
            diagnosis_score=diagnosis_score,
            dimension_scores=dimension_scores or {},
            teacher_comment=teacher_comment,
            standard_diagnosis=standard_diagnosis,
            history_summary=history_summary or {},
        )
        db.add(evaluation)
        await db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(status="evaluated")
        )
        await db.commit()
        return evaluation

    @classmethod
    async def get_evaluation(
        cls, db: DbAsyncSession, session_id: str
    ) -> Evaluation | None:
        """Retrieve evaluation for a session from DB."""
        result = await db.execute(
            select(Evaluation).where(Evaluation.session_id == session_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_evaluation_dict(
        cls, db: DbAsyncSession, session_id: str
    ) -> dict | None:
        """Retrieve evaluation as a dict suitable for API response."""
        ev = await cls.get_evaluation(db, session_id)
        if ev is None:
            return None
        return {
            "evaluation_id": ev.id,
            "session_id": ev.session_id,
            "overall_score": ev.overall_score,
            "consultation_quality": ev.consultation_score,
            "diagnosis_accuracy": ev.diagnosis_score,
            "consultation_dimensions": ev.dimension_scores,
            "diagnosis_dimensions": ev.dimension_scores,
            "teacher_comment": ev.teacher_comment,
            "standard_diagnosis": ev.standard_diagnosis,
            "history_summary": ev.history_summary,
            "created_at": ev.created_at.isoformat() if ev.created_at else "",
        }

    # ═══════════════════════════════════════════════════════════════
    # History listing
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    async def list_sessions(
        cls,
        db: DbAsyncSession,
        user_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Paginated session history with summary data.

        Returns (items: list[dict], total: int).
        """
        # Count
        count_stmt = select(sqlfunc.count()).select_from(Session)
        if user_id:
            count_stmt = count_stmt.where(Session.user_id == user_id)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Query
        query = select(Session).order_by(Session.created_at.desc())
        if user_id:
            query = query.where(Session.user_id == user_id)
        offset = (page - 1) * page_size
        result = await db.execute(query.offset(offset).limit(page_size))
        sessions = result.scalars().all()

        items = []
        for s in sessions:
            items.append({
                "session_id": s.id,
                "case_id": s.case_row,
                "department": s.department,
                "chief_complaint": s.chief_complaint[:80],
                "status": s.status,
                "turn_count": s.turn_count,
                "max_turns": s.max_turns,
                "created_at": s.created_at.isoformat() if s.created_at else "",
            })

        return items, total
