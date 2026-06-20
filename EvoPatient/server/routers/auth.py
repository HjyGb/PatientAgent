"""Auth router — register, login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.dependencies import get_db, hash_password, verify_password, create_access_token
from server.models.user import User
from server.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    QuickLoginRequest,
    UserResponse,
    TokenResponse,
)

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing user
    result = await db.execute(select(User).where(User.employee_id == body.employee_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="工号已存在")

    user = User(
        employee_id=body.employee_id,
        name=body.name,
        password_hash=hash_password(body.password),
        department=body.department,
        role="student",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            employee_id=user.employee_id,
            name=user.name,
            department=user.department,
            role=user.role,
        ),
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.employee_id == body.employee_id))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="工号或密码错误")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            employee_id=user.employee_id,
            name=user.name,
            department=user.department,
            role=user.role,
        ),
    )


@router.post("/auth/quick-login", response_model=TokenResponse)
async def quick_login(body: QuickLoginRequest, db: AsyncSession = Depends(get_db)):
    """Passwordless login by employee ID — auto-creates user on first use.

    Designed for teaching/training scenarios where password management
    is unnecessary overhead. The employee ID alone establishes identity.
    """
    # Try existing user
    result = await db.execute(select(User).where(User.employee_id == body.employee_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-create user on first login
        import uuid as _uuid
        user = User(
            employee_id=body.employee_id,
            name=f"学生{body.employee_id}",
            password_hash=hash_password(str(_uuid.uuid4())),  # random placeholder, not used for auth
            department="",
            role="student",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            employee_id=user.employee_id,
            name=user.name,
            department=user.department,
            role=user.role,
        ),
    )
