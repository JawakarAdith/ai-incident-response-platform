from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings


# Initialize LLM
from langchain_groq import ChatGroq

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    api_key=settings.groq_api_key,
)


PLANNER_SYSTEM_PROMPT = """
You are a Planner Agent in a workflow automation system.

Your job is to:
1. Read the user's request carefully
2. Break it down into clear executable steps
3. Decide which agents are needed

Available agents:
- LogAnalysisAgent: analyzes error logs and finds root cause
- RecommendationAgent: suggests fixes based on analysis
- ToolExecutionAgent: creates Jira tickets and sends Slack messages
- ValidationAgent: validates everything was done correctly

Return your plan as a numbered list.
Be specific and clear.
"""


async def run_planner(user_request: str, logs: str = None) -> str:
    """
    Planner Agent — breaks user request into steps.
    
    Args:
        user_request: what user wants to do
        logs: optional log content
    
    Returns:
        execution plan as string
    """
    
    # Build message
    user_message = f"User request: {user_request}"
    if logs:
        user_message += f"\n\nLogs provided:\n{logs[:500]}"
    
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]
    
    # Call LLM
    response = await llm.ainvoke(messages)
    
    return response.content