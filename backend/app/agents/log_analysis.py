from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=settings.groq_api_key,
)

LOG_ANALYSIS_PROMPT = """
You are a Log Analysis Agent specialized in analyzing application logs.

Your job is to:
1. Read the provided logs carefully
2. Identify error patterns
3. Find the ROOT CAUSE of the issue
4. Extract key information:
   - Error type
   - Affected service
   - Error timestamp
   - Impact (how many users/transactions affected)

Be specific and technical.
Return a clear structured analysis.
"""

async def run_log_analysis(logs: str, plan: str = None) -> str:
    """
    Log Analysis Agent — finds root cause from logs.
    
    Args:
        logs: raw log content
        plan: execution plan from planner
    
    Returns:
        detailed analysis as string
    """
    
    user_message = f"Analyze these logs and find the root cause:\n\n{logs}"
    
    if plan:
        user_message += f"\n\nExecution plan context:\n{plan}"
    
    messages = [
        SystemMessage(content=LOG_ANALYSIS_PROMPT),
        HumanMessage(content=user_message),
    ]
    
    response = await llm.ainvoke(messages)
    return response.content