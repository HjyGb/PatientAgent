"""Sessions router — chat messages, streaming, session state, history."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, get_current_user
from server.schemas.session import (
    SendMessageRequest,
    SendMessageResponse,
    PatientScores,
    SessionInfoResponse,
    SessionSummary,
    HistoryResponse,
)
from server.services.chat_service import ChatService
from server.services.session_service import SessionService

router = APIRouter(tags=["sessions"])


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Send a doctor question and get a patient answer (blocking).

    Persists Q&A to DB and increments turn counter.
    """
    # Verify session exists and is active
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session has ended")

    # Check max turns
    if session.turn_count >= session.max_turns:
        raise HTTPException(status_code=400, detail="Maximum turns reached")

    try:
        result = await ChatService.get_patient_answer(session_id, body.question, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Patient answer failed: {str(e)}")

    scores = result.get("scores", {})
    is_max = result.get("turn", 0) >= session.max_turns

    return SendMessageResponse(
        answer=result["answer"],
        scores=PatientScores(**scores) if scores else None,
        turn=result.get("turn", 0),
        is_max_turns=is_max,
    )


@router.get("/sessions/{session_id}/messages/stream")
async def stream_message(
    session_id: str,
    question: str = Query(..., min_length=1, description="Doctor's question"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """SSE streaming endpoint — token-by-token patient answer.

    Events:
      - patient_token: {token} — one token of the answer
      - patient_complete: {answer, scores, turn, is_max_turns} — final result
      - error: {message} — if something goes wrong
    """
    # Verify session exists and is active
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        try:
            async for event in ChatService.stream_patient_answer(session_id, question, db=db):
                event_type = event["event"]
                data = event["data"]
                if isinstance(data, str) and not data.startswith("{"):
                    yield f"event: {event_type}\ndata: {data}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/info", response_model=SessionInfoResponse)
async def get_session_info(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Info panel data — session metadata, turn count, messages."""
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await SessionService.get_session_history(db, session_id)

    return SessionInfoResponse(
        patient_snapshot=session.chief_complaint,
        department=session.department,
        case_id=session.case_row,
        turn_count=session.turn_count,
        max_turns=session.max_turns,
        status=session.status,
        messages=messages,
        created_at=session.created_at.isoformat() if session.created_at else "",
    )


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """End a consultation session."""
    ok = await SessionService.end_session(db, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "status": "ended"}


@router.get("/sessions/history", response_model=HistoryResponse)
async def session_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Past session list for the current user (DB-backed).

    When user is authenticated, only returns their sessions.
    When anonymous, returns all sessions.
    """
    items, total = await SessionService.list_sessions(
        db,
        user_id=str(user.id) if user else None,
        page=page,
        page_size=page_size,
    )

    return HistoryResponse(
        items=[SessionSummary(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
