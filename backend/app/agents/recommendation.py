from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    api_key=settings.groq_api_key,
)

RECOMMENDATION_PROMPT = """
You are a Recommendation Agent specialized in suggesting fixes for technical issues.

Your job is to:
1. Read the log analysis provided
2. Check if any past similar incidents are provided
3. If past incidents found → prioritize those proven fixes!
4. Suggest specific actionable fixes
5. Determine priority (Low/Medium/High/Critical)
6. Identify which team should handle it
7. Estimate time to fix

If past incidents are provided:
→ Reference them specifically
→ Say "Based on past incident JIRA-XXX..."
→ Use proven fixes first!

Always provide:
- Immediate fix (quick solution)
- Permanent fix (long term solution)
- Priority level
- Team to assign
- Estimated resolution time

Be specific and actionable.
"""

async def run_recommendation(
    root_cause: str,
    logs: str = None,
    rag_context: str = None
) -> str:

    print("✅ run_recommendation CALLED")
    print("rag_context =", rag_context)

    user_message = f"Based on this analysis, suggest fixes:\n\n{root_cause}"

    if logs:
        user_message += f"\n\nOriginal logs for context:\n{logs[:300]}"

    # Inject RAG context if available
    if rag_context:
        user_message += f"\n\n{rag_context}"
        user_message += "\nPlease reference these past incidents in your recommendation!"

    messages = [
        SystemMessage(content=RECOMMENDATION_PROMPT),
        HumanMessage(content=user_message),
    ]

    response = await llm.ainvoke(messages)
    return response.content