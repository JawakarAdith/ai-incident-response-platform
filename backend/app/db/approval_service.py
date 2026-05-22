import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import WorkflowApproval, Workflow


async def create_approval_request(
    db: AsyncSession,
    workflow_id: str,
    confidence_score: float,
    reason: str
) -> WorkflowApproval:
    """Create approval request when confidence is low."""
    approval = WorkflowApproval(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        status="PENDING",
        confidence_score=confidence_score,
        reason=reason
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    return approval


async def get_pending_approvals(
    db: AsyncSession
) -> list:
    """Get all pending approval requests."""
    result = await db.execute(
        select(WorkflowApproval).where(
            WorkflowApproval.status == "PENDING"
        ).order_by(WorkflowApproval.created_at.desc())
    )
    return result.scalars().all()


async def approve_workflow(
    db: AsyncSession,
    workflow_id: str,
    reviewed_by: str
) -> None:
    """Approve a workflow."""
    result = await db.execute(
        select(WorkflowApproval).where(
            WorkflowApproval.workflow_id == workflow_id
        )
    )
    approval = result.scalar_one_or_none()
    if approval:
        approval.status = "APPROVED"
        approval.reviewed_by = reviewed_by
        await db.commit()

    # Update workflow status
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id
        )
    )
    workflow = result.scalar_one_or_none()
    if workflow:
        workflow.status = "COMPLETED"
        await db.commit()


async def reject_workflow(
    db: AsyncSession,
    workflow_id: str,
    reviewed_by: str,
    reason: str
) -> None:
    """Reject a workflow."""
    result = await db.execute(
        select(WorkflowApproval).where(
            WorkflowApproval.workflow_id == workflow_id
        )
    )
    approval = result.scalar_one_or_none()
    if approval:
        approval.status = "REJECTED"
        approval.reviewed_by = reviewed_by
        approval.reason = reason
        await db.commit()

    # Update workflow status
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id
        )
    )
    workflow = result.scalar_one_or_none()
    if workflow:
        workflow.status = "REJECTED"
        await db.commit()