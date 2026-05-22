from jira import JIRA
from app.core.config import settings


def get_jira_client() -> JIRA:
    """Create and return Jira client."""
    return JIRA(
        server=settings.jira_base_url,
        basic_auth=(settings.jira_email, settings.jira_api_token)
    )


async def create_jira_ticket(
    title: str,
    description: str,
    priority: str = "High"
) -> str:
    """
    Create a Jira ticket.
    
    Args:
        title: ticket title
        description: ticket description
        priority: Low, Medium, High, Critical
    
    Returns:
        ticket ID (e.g. OPS-42)
    """
    try:
        jira = get_jira_client()
        
        issue = jira.create_issue(
            project=settings.jira_project_key,
            summary=title,
            description=description,
            issuetype={"name": "Bug"},
            priority={"name": priority}
        )
        
        return issue.key
    
    except Exception as e:
        print(f"Jira error: {e}")
        return f"JIRA-ERROR: {str(e)}"


async def get_jira_ticket(ticket_id: str) -> dict:
    """
    Get Jira ticket details.
    
    Args:
        ticket_id: e.g. OPS-42
    
    Returns:
        ticket details as dict
    """
    try:
        jira = get_jira_client()
        issue = jira.issue(ticket_id)
        
        return {
            "id": issue.key,
            "title": issue.fields.summary,
            "status": issue.fields.status.name,
            "priority": issue.fields.priority.name,
        }
    
    except Exception as e:
        print(f"Jira error: {e}")
        return {"error": str(e)}