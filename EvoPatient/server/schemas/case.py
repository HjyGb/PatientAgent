"""Case schemas — patient case list and detail."""

from pydantic import BaseModel, Field


class CaseSummary(BaseModel):
    """A single case in the paginated list."""
    id: int = Field(..., description="Row number in the Excel sheet")
    serial_number: str = ""
    department: str = ""
    preview: str = ""          # First ~200 characters of the case
    difficulty: int = 1        # 1-3
    case_length: int = 0
    practice_count: int = 0    # How many students have practiced this case


class CaseListResponse(BaseModel):
    items: list[CaseSummary]
    total: int
    page: int
    page_size: int


class CaseLoadResponse(BaseModel):
    """Returned when a case is loaded (initializes a session)."""
    session_id: str
    case_id: int
    department: str
    chief_complaint: str
