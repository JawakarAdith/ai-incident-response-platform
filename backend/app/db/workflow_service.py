import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Workflow, WorkflowStep, ExecutionLog


async def create_workflow(
    db: AsyncSession,
    title: str,
    input_data: str,
    created_by: str
) -> Workflow:
    """Create a new workflow record in DB."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        title=title,
        status="RUNNING",
        input_data=input_data,
        created_by=created_by,
        updated_by=created_by
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


async def update_workflow(
    db: AsyncSession,
    workflow_id: str,
    status: str,
    output_data: dict
) -> None:
    """Update workflow status and output."""
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if workflow:
        workflow.status = status
        workflow.output_data = json.dumps(output_data)
        await db.commit()


async def create_workflow_step(
    db: AsyncSession,
    workflow_id: str,
    step_name: str,
    step_order: int,
    agent_name: str,
    input_data: str,
    output_data: str,
    status: str = "COMPLETED"
) -> WorkflowStep:
    """Create a workflow step record."""
    step = WorkflowStep(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        step_name=step_name,
        step_order=step_order,
        agent_name=agent_name,
        input_data=input_data,
        output_data=output_data,
        status=status
    )
    db.add(step)
    await db.commit()
    return step


async def create_execution_log(
    db: AsyncSession,
    workflow_id: str,
    level: str,
    message: str,
    agent_name: str = None
) -> None:
    """Create an execution log entry."""
    log = ExecutionLog(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        level=level,
        message=message,
        agent_name=agent_name
    )
    db.add(log)
    await db.commit()


async def get_workflow(
    db: AsyncSession,
    workflow_id: str
) -> Workflow:
    """Get workflow by ID."""
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    return result.scalar_one_or_none()


async def get_all_workflows(
    db: AsyncSession
) -> list:
    """Get all workflows."""
    result = await db.execute(
        select(Workflow).order_by(Workflow.created_at.desc())
    )
    return result.scalars().all()

async def get_steps_by_workflow(
    db: AsyncSession,
    workflow_id: str
) -> list:
    """Get all steps for a given workflow ID."""
    from app.db.models import WorkflowStep
    from sqlalchemy import select

    result = await db.execute(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.step_order)
    )
    return result.scalars().all()