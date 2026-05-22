from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from app.db.database import get_db
from app.agents.workflow import workflow
from app.db.workflow_service import (
    create_workflow,
    update_workflow,
    create_workflow_step,
    create_execution_log,
    get_workflow,
    get_all_workflows
)
from app.core.security import decode_token

router = APIRouter(prefix="/workflow", tags=["workflow"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class WorkflowRequest(BaseModel):
    task: str
    logs: Optional[str] = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    root_cause: Optional[str]
    recommendation: Optional[str]
    jira_ticket_id: Optional[str]
    slack_sent: Optional[bool]
    confidence_score: Optional[float]


@router.post("/run", response_model=WorkflowResponse)
async def run_workflow(
    request: WorkflowRequest,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    # Authenticate user
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_email = payload.get("sub")

    # Step 1: Create workflow record in DB
    db_workflow = await create_workflow(
        db=db,
        title=request.task[:100],
        input_data=request.logs or "",
        created_by=user_email
    )

    await create_execution_log(
        db=db,
        workflow_id=db_workflow.id,
        level="INFO",
        message="Workflow started",
        agent_name=None
    )

    try:
        # Step 2: Run LangGraph workflow
        result = await workflow.ainvoke({
            "user_request": request.task,
            "logs": request.logs,
            "plan": None,
            "root_cause": None,
            "recommendation": None,
            "jira_ticket_id": None,
            "slack_sent": None,
            "confidence_score": None,
            "validation_details": None,
            "rag_context": None,
            "low_confidence": None,
            "error": None
        })

        # Step 3: Save each agent step to DB — correct order
        confidence = result.get("confidence_score", 0)
        is_low_confidence = confidence < 0.75

        steps = [
            (
                "Planner Agent", 1, "PlannerAgent",
                request.task,
                result.get("plan", "")
            ),
            (
                "RAG Search", 2, "RAGSearchAgent",
                request.task,
                result.get("rag_context") or "No similar incidents found"
            ),
            (
                "Log Analysis", 3, "LogAnalysisAgent",
                request.logs or "",
                result.get("root_cause", "")
            ),
            (
                "Recommendation", 4, "RecommendationAgent",
                result.get("root_cause", ""),
                result.get("recommendation", "")
            ),
            (
                "Validation", 5, "ValidationAgent",
                result.get("recommendation", ""),
                f"Score: {confidence:.0%} | Low confidence: {is_low_confidence}"
            ),
            (
                "Tool Execution", 6, "ToolExecutionAgent",
                result.get("recommendation", ""),
                f"Jira: {result.get('jira_ticket_id')} | Slack: {result.get('slack_sent')}"
            ),
        ]

        for step_name, order, agent_name, input_data, output_data in steps:
            await create_workflow_step(
                db=db,
                workflow_id=db_workflow.id,
                step_name=step_name,
                step_order=order,
                agent_name=agent_name,
                input_data=input_data[:500] if input_data else "",
                output_data=output_data[:500] if output_data else "",
                status="COMPLETED"
            )
            await create_execution_log(
                db=db,
                workflow_id=db_workflow.id,
                level="INFO",
                message=f"{agent_name} completed successfully",
                agent_name=agent_name
            )

        # Step 4: Determine final status — no approval gate
        final_status = "COMPLETED_LOW_CONFIDENCE" if is_low_confidence else "COMPLETED"

        await update_workflow(
            db=db,
            workflow_id=db_workflow.id,
            status=final_status,
            output_data={
                "root_cause":       result.get("root_cause"),
                "recommendation":   result.get("recommendation"),
                "jira_ticket_id":   result.get("jira_ticket_id"),
                "slack_sent":       result.get("slack_sent"),
                "confidence_score": confidence
            }
        )

        # Step 5: Log final result
        level = "WARNING" if is_low_confidence else "INFO"
        message = (
            f"Completed with low confidence ({confidence:.0%}). "
            f"Jira ticket {result.get('jira_ticket_id')} flagged for review."
            if is_low_confidence
            else f"Workflow completed successfully. "
                 f"Jira ticket {result.get('jira_ticket_id')} created."
        )

        await create_execution_log(
            db=db,
            workflow_id=db_workflow.id,
            level=level,
            message=message,
            agent_name=None
        )

        return WorkflowResponse(
            workflow_id=db_workflow.id,
            status=final_status,
            root_cause=result.get("root_cause"),
            recommendation=result.get("recommendation"),
            jira_ticket_id=result.get("jira_ticket_id"),
            slack_sent=result.get("slack_sent"),
            confidence_score=confidence
        )

    except Exception as e:
        await update_workflow(
            db=db,
            workflow_id=db_workflow.id,
            status="FAILED",
            output_data={"error": str(e)}
        )
        await create_execution_log(
            db=db,
            workflow_id=db_workflow.id,
            level="ERROR",
            message=f"Workflow failed: {str(e)}",
            agent_name=None
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    workflows = await get_all_workflows(db)
    return [
        {
            "id": w.id,
            "title": w.title,
            "status": w.status,
            "confidence_score": w.confidence_score,
            "created_at": str(w.created_at),
            "created_by": w.created_by
        }
        for w in workflows
    ]


@router.get("/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    wf = await get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "id": wf.id,
        "title": wf.title,
        "status": wf.status,
        "output_data": wf.output_data,
        "created_at": str(wf.created_at),
        "created_by": wf.created_by
    }

# @router.get("/{workflow_id}/steps")
# async def get_workflow_steps_api(
#     workflow_id: str,
#     db: AsyncSession = Depends(get_db),
#     token: str = Depends(oauth2_scheme)
# ):
#     """
#     Get all workflow execution steps for timeline visualization.
#     """
#     payload = decode_token(token)
#     if not payload:
#         raise HTTPException(status_code=401, detail="Invalid token")

#     wf = await get_workflow(db, workflow_id)
#     if not wf:
#         raise HTTPException(status_code=404, detail="Workflow not found")

#     # Import here to avoid circular imports
#     from app.db.workflow_service import get_workflow_steps

#     steps = await get_workflow_steps(db, workflow_id)

#     return [
#         {
#             "id": step.id,
#             "step_name": step.step_name,
#             "step_order": step.step_order,
#             "agent_name": step.agent_name,
#             "input_data": step.input_data,
#             "output_data": step.output_data,
#             "status": step.status,
#             "started_at": str(step.started_at) if step.started_at else None,
#             "completed_at": str(step.completed_at) if step.completed_at else None
#         }
#         for step in steps
#     ]

@router.get("/{workflow_id}/steps")
async def get_workflow_steps(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Get all agent steps for a workflow."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.db.workflow_service import get_steps_by_workflow

    steps = await get_steps_by_workflow(db, workflow_id)
    if steps is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return [
        {
            "id":           s.id,
            "step_name":    s.step_name,
            "step_order":   s.step_order,
            "agent_name":   s.agent_name,
            "input_data":   s.input_data,
            "output_data":  s.output_data,
            "status":       s.status,
            "created_at":   str(s.created_at)
        }
        for s in sorted(steps, key=lambda x: x.step_order)
    ]