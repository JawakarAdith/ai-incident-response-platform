from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


# Create async engine — this is the connection to PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # logs all SQL queries in development
)

# Session factory — used to talk to the database
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class — all our database models will inherit from this
class Base(DeclarativeBase):
    pass

# Dependency — used in FastAPI routes to get a database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise




async def get_workflow_steps(db, workflow_id: str):
    result = await db.execute(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.step_order)
    )
    return result.scalars().all()