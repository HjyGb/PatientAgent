"""Evaluation schemas — diagnosis submission and AI assessment."""

from pydantic import BaseModel, Field


class DiagnosisSubmission(BaseModel):
    primary_diagnosis: str = Field(..., min_length=1, max_length=2000, description="初步诊断")
    evidence: str = Field(..., min_length=1, max_length=5000, description="诊断依据")
    differential_diagnosis: str = Field(default="", max_length=2000, description="鉴别诊断")
    suggested_tests: str = Field(default="", max_length=2000, description="建议检查")


class DimensionScore(BaseModel):
    score: float
    max_score: int = 5
    reason: str = ""


class EvaluationResponse(BaseModel):
    evaluation_id: str
    session_id: str
    overall_score: float
    consultation_quality: float
    diagnosis_accuracy: float
    consultation_dimensions: dict[str, DimensionScore]
    diagnosis_dimensions: dict[str, DimensionScore]
    teacher_comment: str
    standard_diagnosis: str
    history_summary: dict[str, str]  # personal Hx, physical exam, auxiliary exam, family Hx
    created_at: str
