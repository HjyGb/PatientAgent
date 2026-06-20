"""Evaluations router — submit diagnosis, get AI evaluation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, get_current_user
from server.schemas.evaluation import DiagnosisSubmission, EvaluationResponse, DimensionScore
from server.services.evaluation_service import EvaluationService
from server.services.session_service import SessionService

router = APIRouter(tags=["evaluations"])


@router.post("/sessions/{session_id}/diagnosis")
async def submit_diagnosis(
    session_id: str,
    body: DiagnosisSubmission,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Submit student diagnosis for AI evaluation.

    Triggers the full evaluation pipeline:
    1. Generate ground truth diagnosis from full patient record
    2. LLM compares student vs ground truth on 4 dimensions
    3. Compute composite scores and teacher comment
    4. Persist to database
    """
    # Verify session exists
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = await EvaluationService.evaluate_diagnosis(
            session_id,
            {
                "primary_diagnosis": body.primary_diagnosis,
                "evidence": body.evidence,
                "differential_diagnosis": body.differential_diagnosis,
                "suggested_tests": body.suggested_tests,
            },
            db=db,
        )
        return {"evaluation_id": result["evaluation_id"], "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/sessions/{session_id}/evaluation", response_model=EvaluationResponse)
async def get_evaluation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get the full evaluation report for a session.

    Tries DB first, then in-memory cache as fallback.
    """
    # Try DB first
    result = await EvaluationService.get_evaluation_from_db(session_id, db)

    # Fallback to in-memory cache
    if result is None:
        result = EvaluationService.get_cached_evaluation(session_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not yet submitted. POST to /sessions/{session_id}/diagnosis first.",
        )

    # Build dimension score objects
    consultation_dims = {}
    diagnosis_dims = {}
    for key, val in result.get("consultation_dimensions", {}).items():
        consultation_dims[key] = DimensionScore(
            score=val.get("score", 3.0),
            max_score=val.get("max_score", 5),
            reason=val.get("reason", ""),
        )
    for key, val in result.get("diagnosis_dimensions", {}).items():
        diagnosis_dims[key] = DimensionScore(
            score=val.get("score", 3.0),
            max_score=val.get("max_score", 5),
            reason=val.get("reason", ""),
        )

    return EvaluationResponse(
        evaluation_id=result["evaluation_id"],
        session_id=result["session_id"],
        overall_score=result["overall_score"],
        consultation_quality=result["consultation_quality"],
        diagnosis_accuracy=result["diagnosis_accuracy"],
        consultation_dimensions=consultation_dims,
        diagnosis_dimensions=diagnosis_dims,
        teacher_comment=result["teacher_comment"],
        standard_diagnosis=result["standard_diagnosis"],
        history_summary=result.get("history_summary", {}),
        created_at=result.get("created_at", ""),
    )
