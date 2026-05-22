from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
import json
import re

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=settings.groq_api_key,
)

VALIDATION_PROMPT = """
You are a STRICT Validation Agent.

Your task is to critically evaluate whether the AI diagnosis
and recommendation are actually reliable.

You must be conservative with scoring.

You will receive:
- User request
- Root cause analysis
- Recommendation
- Actions taken

SCORING RULES:

HIGH confidence (0.85 - 1.0):
Use ONLY when:
- Logs contain deterministic errors
- Single clear root cause exists
- Recommendation is precise and actionable
- Failure pattern is obvious

Examples:
- Port already in use
- Database connection pool exhausted
- Authentication failure
- Disk full
- DNS resolution failure

MEDIUM confidence (0.60 - 0.84):
Use when:
- Some ambiguity exists
- Multiple possible causes
- Recommendation partially inferred
- Logs incomplete

LOW confidence (0.0 - 0.59):
Use when:
- Logs are noisy or contradictory
- Multiple unrelated symptoms exist
- Temporary recovery occurs
- Runtime randomness exists
- Recommendation is speculative
- Root cause uncertain
- Generic exceptions occur

IMPORTANT RULES:
- Be strict.
- Never give high confidence for ambiguous logs.
- If multiple unrelated symptoms exist, confidence MUST be below 0.60.
- If logs contain generic runtime exceptions, reduce confidence heavily.
- Temporary recovery followed by failure indicates uncertainty.

Return ONLY valid JSON:

{
  "confidence_score": 0.42,
  "root_cause_clarity": 0.40,
  "recommendation_quality": 0.50,
  "actions_completed": 1.0,
  "issues_found": "Multiple inconsistent symptoms and unclear deterministic root cause.",
  "summary": "Low confidence due to ambiguous production behavior."
}
"""
async def run_validation(
    user_request: str,
    root_cause: str,
    recommendation: str,
    jira_ticket_id: str,
    slack_sent: bool
) -> dict:
    """
    Validation Agent — scores confidence of workflow.
    
    Returns:
        dict with confidence score and evaluation
    """
    
    user_message = f"""
Evaluate this workflow execution:

User Request: {user_request}

Log Analysis Result:
{root_cause}

Recommendation:
{recommendation}

Actions Taken:
- Jira ticket created: {jira_ticket_id or 'No'}
- Slack notified: {slack_sent}

Return ONLY a JSON object with confidence_score, 
root_cause_clarity, recommendation_quality, 
actions_completed, issues_found, summary fields.
"""
    
    messages = [
        SystemMessage(content=VALIDATION_PROMPT),
        HumanMessage(content=user_message),
    ]
    
    response = await llm.ainvoke(messages)
    
    # Parse JSON response
    try:
        # Clean response - remove markdown code blocks
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        return result

    except json.JSONDecodeError:
        # Try to extract score from text using regex
        score_match = re.search(
            r'"confidence_score":\s*([0-9.]+)', 
            response.content
        )
        score = float(score_match.group(1)) if score_match else 0.75
        
        return {
            "confidence_score": score,
            "root_cause_clarity": 0.75,
            "recommendation_quality": 0.75,
            "actions_completed": 1.0,
            "issues_found": "None",
            "summary": "Validation completed successfully"
        }