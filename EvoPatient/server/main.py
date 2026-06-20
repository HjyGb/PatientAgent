"""PatientAgent FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
from server.dependencies import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    # Import models so they register with Base.metadata
    import server.models  # noqa: F811
    # Create tables on startup (for dev; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed test user if not exists
    from server.dependencies import async_session, hash_password
    from server.models.user import User
    from sqlalchemy import select
    async with async_session() as db:
        result = await db.execute(select(User).where(User.employee_id == "000000"))
        if result.scalar_one_or_none() is None:
            import uuid as _uuid
            user = User(
                employee_id="000000",
                name="测试用户",
                password_hash=hash_password(str(_uuid.uuid4())),
                department="",
                role="student",
            )
            db.add(user)
            await db.commit()

    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──
@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# ── Register routers ──
from server.routers.auth import router as auth_router
from server.routers.cases import router as cases_router
from server.routers.sessions import router as sessions_router
from server.routers.evaluations import router as evaluations_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(evaluations_router, prefix="/api/v1")
