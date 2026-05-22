from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.workflow import router as workflow_router
from app.api.approval import router as approval_router
from app.api.memory import router as memory_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Workflow Platform...")
    print("✅ Platform ready!")
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Multi-Agent AI Workflow Automation Platform",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(f"{settings.api_prefix}/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(workflow_router, prefix=settings.api_prefix)
app.include_router(approval_router, prefix=settings.api_prefix)
app.include_router(memory_router, prefix=settings.api_prefix)