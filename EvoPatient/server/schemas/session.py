"""Session schemas — chat messages, session info."""

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class PatientScores(BaseModel):
    overall: int = 0
    relevance: int = 0
    faithfulness: int = 0
    robustness: int = 0


class SendMessageResponse(BaseModel):
    answer: str
    scores: PatientScores | None = None
    turn: int
    is_max_turns: bool


class ConfirmedInfo(BaseModel):
    category: str = ""
    detail: str = ""
    turn_discovered: int = 0


class SessionInfoResponse(BaseModel):
    patient_snapshot: str = ""
    confirmed_info: list[ConfirmedInfo] = []
    coverage: float = 0.0
    suggestions: list[str] = []
    department: str = ""
    case_id: int = 0
    turn_count: int = 0
    max_turns: int = 12
    status: str = "active"
    messages: list[dict] = []
    created_at: str = ""


class SessionSummary(BaseModel):
    """A past session in the history list."""
    session_id: str
    case_id: int
    department: str
    chief_complaint: str
    turn_count: int
    status: str
    created_at: str


class HistoryResponse(BaseModel):
    items: list[SessionSummary]
    total: int
    page: int
    page_size: int
