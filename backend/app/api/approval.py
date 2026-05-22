from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.core.security import decode_token
from app.db.approval_service import (
    get_pending_approvals,
    approve_workflow,
    reject_workflow
)

router = APIRouter(prefix="/approval", tags=["approval"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class RejectRequest(BaseModel):
    reason: str


@router.get("/pending")
async def get_pending(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Get all pending approval requests."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    approvals = await get_pending_approvals(db)
    return [
        {
            "id": a.id,
            "workflow_id": a.workflow_id,
            "status": a.status,
            "confidence_score": a.confidence_score,
            "reason": a.reason,
            "created_at": str(a.created_at)
        }
        for a in approvals
    ]


@router.post("/{workflow_id}/approve")
async def approve(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Approve a workflow."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_email = payload.get("sub")
    await approve_workflow(db, workflow_id, user_email)
    return {"message": "Workflow approved successfully!"}


@router.post("/{workflow_id}/reject")
async def reject(
    workflow_id: str,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Reject a workflow."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_email = payload.get("sub")
    await reject_workflow(
        db, workflow_id, user_email, request.reason
    )
    return {"message": "Workflow rejected!"}