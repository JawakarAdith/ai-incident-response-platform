from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.agents.planner import run_planner
from app.agents.log_analysis import run_log_analysis
from app.agents.recommendation import run_recommendation
from app.agents.validation import run_validation


# ── State ──────────────────────────────────────────────────

class WorkflowState(TypedDict):
    user_request: str
    logs: Optional[str]
    plan: Optional[str]
    root_cause: Optional[str]
    recommendation: Optional[str]
    jira_ticket_id: Optional[str]
    slack_sent: Optional[bool]
    confidence_score: Optional[float]
    validation_details: Optional[dict]
    rag_context: Optional[str]
    low_confidence: Optional[bool]   # ← NEW: flag for warning label
    error: Optional[str]


# ── Agent Nodes ────────────────────────────────────────────

async def planner_node(state: WorkflowState) -> dict:
    print("🧠 Planner Agent running...")
    plan = await run_planner(
        user_request=state["user_request"],
        logs=state.get("logs")
    )
    print("✅ Plan created!")
    return {"plan": plan}


async def rag_search_node(state: WorkflowState) -> dict:
    print("🔍 RAG Memory searching...")
    from app.memory.rag_service import get_rag_context
    problem = f"{state.get('user_request', '')} {state.get('logs', '')[:200]}"
    rag_context = await get_rag_context(problem)
    if rag_context:
        print("✅ Found similar past incidents!")
    else:
        print("📭 No similar past incidents found")
    return {"rag_context": rag_context}


async def log_analysis_node(state: WorkflowState) -> dict:
    print("🔍 Log Analysis Agent running...")
    root_cause = await run_log_analysis(
        logs=state.get("logs", "No logs provided"),
        plan=state.get("plan")
    )
    print("✅ Root cause found!")
    return {"root_cause": root_cause}


async def recommendation_node(state: WorkflowState) -> dict:
    print("💡 Recommendation Agent running...")
    recommendation = await run_recommendation(
        root_cause=state.get("root_cause", ""),
        logs=state.get("logs"),
        rag_context=state.get("rag_context")
    )
    print("✅ Recommendation created!")
    return {"recommendation": recommendation}


async def validation_node(state: WorkflowState) -> dict:
    """
    Scores the recommendation BEFORE any tools run.
    Only uses: user_request, root_cause, recommendation.
    Does NOT need jira_ticket_id or slack_sent.
    """
    print("✅ Validation Agent running...")
    result = await run_validation(
        user_request=state["user_request"],
        root_cause=state.get("root_cause", ""),
        recommendation=state.get("recommendation", ""),
        jira_ticket_id=None,   # not created yet — intentional
        slack_sent=None        # not sent yet — intentional
    )
    score = result.get("confidence_score", 0.70)
    print(f"✅ Confidence score: {score}")
    return {
        "confidence_score": score,
        "validation_details": result,
        "low_confidence": score < 0.75   # ← flag carries into tool_execution
    }


async def tool_execution_node(state: WorkflowState) -> dict:
    """
    Always creates Jira + sends Slack.
    Low confidence → adds WARNING label + warning message.
    High confidence → normal ticket + clean message.
    """
    print("🔧 Tool Execution Agent running...")

    from app.tools.jira_tool import create_jira_ticket
    from app.tools.slack_tool import send_incident_notification

    root_cause = state.get("root_cause", "Unknown issue")
    recommendation = state.get("recommendation", "Not available")
    score = state.get("confidence_score", 0.0)
    is_low_confidence = state.get("low_confidence", False)

    # ── Jira ticket title ──────────────────────────────────
    if is_low_confidence:
        title = f"⚠️ [LOW CONFIDENCE] Incident: {root_cause[:80]}".replace('\n', ' ')
    else:
        title = f"Incident: {root_cause[:100]}".replace('\n', ' ')

    # ── Jira ticket description ────────────────────────────
    confidence_warning = ""
    if is_low_confidence:
        confidence_warning = f"""
⚠️ WARNING — LOW CONFIDENCE ANALYSIS
AI confidence score: {score:.0%}
This ticket was auto-generated but requires human verification
before acting on the recommendation below.
{'─' * 50}
"""

    description = f"""
Workflow Automation Platform — Auto Generated Ticket
{confidence_warning}
User Request:
{state.get('user_request', '')}

Root Cause Analysis:
{root_cause}

AI Recommendation:
{recommendation}

Logs:
{state.get('logs', 'No logs provided')[:500]}

Confidence Score: {score:.0%}
    """

    # ── Create Jira ticket ─────────────────────────────────
    jira_ticket_id = await create_jira_ticket(
        title=title,
        description=description,
        priority="High" if not is_low_confidence else "Medium"
    )
    print(f"✅ Jira ticket created: {jira_ticket_id}")

    # ── Send Slack notification ────────────────────────────
    slack_sent = await send_incident_notification(
        jira_ticket_id=jira_ticket_id,
        root_cause=root_cause[:200],
        recommendation=recommendation[:200],
        confidence_score=score
    )
    print(f"✅ Slack notified: {slack_sent}")

    return {
        "jira_ticket_id": jira_ticket_id,
        "slack_sent": slack_sent
    }


# ── Conditional edge ───────────────────────────────────────

def decide_after_validation(state: WorkflowState) -> str:
    """
    After validation, always proceed to tool_execution.
    The low_confidence flag inside tool_execution handles
    the warning label — no dead ends, no broken flows.
    """
    score = state.get("confidence_score", 0)
    print(f"🔀 Routing decision: score={score:.2f} → tool_execution")
    return "tool_execution"


# ── Build Graph ────────────────────────────────────────────

def build_workflow() -> StateGraph:
    graph = StateGraph(WorkflowState)

    # Register nodes
    graph.add_node("planner",        planner_node)
    graph.add_node("rag_search",     rag_search_node)
    graph.add_node("log_analysis",   log_analysis_node)
    graph.add_node("recommendation", recommendation_node)
    graph.add_node("validation",     validation_node)       # ← moved before tools
    graph.add_node("tool_execution", tool_execution_node)   # ← moved after validation

    # Define order
    graph.set_entry_point("planner")
    graph.add_edge("planner",        "rag_search")
    graph.add_edge("rag_search",     "log_analysis")
    graph.add_edge("log_analysis",   "recommendation")
    graph.add_edge("recommendation", "validation")          # ← validation first

    # Conditional edge from validation
    graph.add_conditional_edges(
        "validation",
        decide_after_validation,
        {"tool_execution": "tool_execution"}
    )

    graph.add_edge("tool_execution", END)

    return graph.compile()


workflow = build_workflow()