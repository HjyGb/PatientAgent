"""Cases router — list, preview, load patient cases."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, get_current_user
from server.schemas.case import CaseSummary, CaseListResponse, CaseLoadResponse
from server.services.case_service import CaseService
from server.services.session_service import SessionService

router = APIRouter(tags=["cases"])


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    department: str = Query(default="全部", description="科室筛选"),
    difficulty: str = Query(default="全部", description="难度筛选 1/2/3"),
    search: str = Query(default="", description="文本搜索"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of available patient cases with filtering."""
    items, total = CaseService.list_cases(
        department=department,
        difficulty=difficulty,
        search=search,
        page=page,
        page_size=page_size,
    )
    return CaseListResponse(
        items=[CaseSummary(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/cases/{case_id}")
async def get_case_detail(case_id: int, db: AsyncSession = Depends(get_db)):
    """Preview a case (no full record revealed — only summary for fairness)."""
    all_cases = CaseService._load_all_cases()
    for c in all_cases:
        if c["id"] == case_id:
            return {
                "id": c["id"],
                "serial_number": c["serial_number"],
                "department": c["department"],
                "preview": c["preview"],
                "difficulty": c["difficulty"],
                "case_length": c["case_length"],
                "practice_count": c["practice_count"],
            }
    raise HTTPException(status_code=404, detail="Case not found")


@router.post("/cases/{case_id}/load", response_model=CaseLoadResponse)
async def load_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Initialize a consultation session from a case.

    This triggers the full pipeline:
    1. Read patient data from Excel
    2. Apply vagueness obfuscation
    3. Assign medical department
    4. Generate chief complaint
    5. Create DB session record (persistent)
    """
    try:
        result = CaseService.load_patient(
            sheet_name="病程记录_首次病程",
            row_number=case_id,
            col_number=1,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Dataset Excel file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")

    # Create persistent DB session
    session = await SessionService.create_session(
        db,
        case_row=result["case_id"],
        sheet_name=result["sheet_name"],
        department=result["department"],
        chief_complaint=result["chief_complaint"],
        user_id=str(user.id) if user else None,
    )

    # Register the in-memory context for live agent access
    ctx = result["_context"]
    SessionService.register_context(session.id, ctx)

    return CaseLoadResponse(
        session_id=session.id,
        case_id=result["case_id"],
        department=result["department"],
        chief_complaint=result["chief_complaint"],
    )


@router.get("/departments")
async def list_departments():
    """Return the list of available departments for the filter dropdown."""
    from server.services.case_service import DEPARTMENT_KEYWORDS
    return {"departments": list(DEPARTMENT_KEYWORDS.keys())}
