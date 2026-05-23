import pytest
from unittest.mock import AsyncMock, patch


class TestJiraIntegration:

    @pytest.mark.asyncio
    async def test_high_confidence_ticket_has_no_warning(self):
        """High confidence → Jira title must NOT contain warning label."""
        from app.agents.workflow import tool_execution_node

        state = {
            "user_request":    "Analyze deployment failure",
            "root_cause":      "Database connection pool exhausted",
            "recommendation":  "Increase pool size to 300, restart service",
            "logs":            "ERROR connection pool exhausted",
            "confidence_score": 0.88,
            "low_confidence":  False
        }

        with patch("app.tools.jira_tool.create_jira_ticket") as mock_jira, \
             patch("app.tools.slack_tool.send_incident_notification") as mock_slack:

            mock_jira.return_value  = AsyncMock(return_value="SCRUM-999")
            mock_slack.return_value = AsyncMock(return_value=True)

            mock_jira.side_effect = None
            mock_jira.return_value = "SCRUM-999"
            mock_slack.return_value = True

            captured_title = {}

            async def capture_jira(title, description, priority):
                captured_title["title"] = title
                return "SCRUM-999"

            mock_jira.side_effect = capture_jira

            await tool_execution_node(state)

        assert "LOW CONFIDENCE" not in captured_title.get("title", ""), (
            f"High confidence ticket should not have warning. "
            f"Title: {captured_title.get('title')}"
        )
        assert "⚠️" not in captured_title.get("title", ""), (
            "High confidence ticket should not have warning emoji"
        )

    @pytest.mark.asyncio
    async def test_low_confidence_ticket_has_warning_label(self):
        """Low confidence → Jira title must contain warning label."""
        from app.agents.workflow import tool_execution_node

        state = {
            "user_request":    "Something is wrong",
            "root_cause":      "Unknown error occurred",
            "recommendation":  "Check the service",
            "logs":            "ERROR something failed",
            "confidence_score": 0.45,
            "low_confidence":  True
        }

        captured_title = {}

        with patch("app.tools.jira_tool.create_jira_ticket") as mock_jira, \
             patch("app.tools.slack_tool.send_incident_notification") as mock_slack:

            async def capture_jira(title, description, priority):
                captured_title["title"] = title
                return "SCRUM-998"

            mock_jira.side_effect  = capture_jira
            mock_slack.return_value = True

            await tool_execution_node(state)

        assert "LOW CONFIDENCE" in captured_title.get("title", ""), (
            f"Low confidence ticket must have warning label. "
            f"Title: {captured_title.get('title')}"
        )

    @pytest.mark.asyncio
    async def test_low_confidence_ticket_is_medium_priority(self):
        """Low confidence → Jira priority should be Medium not High."""
        from app.agents.workflow import tool_execution_node

        state = {
            "user_request":    "Something is wrong",
            "root_cause":      "Unknown error",
            "recommendation":  "Check service",
            "logs":            "ERROR something failed",
            "confidence_score": 0.45,
            "low_confidence":  True
        }

        captured_priority = {}

        with patch("app.tools.jira_tool.create_jira_ticket") as mock_jira, \
             patch("app.tools.slack_tool.send_incident_notification") as mock_slack:

            async def capture_jira(title, description, priority):
                captured_priority["priority"] = priority
                return "SCRUM-997"

            mock_jira.side_effect  = capture_jira
            mock_slack.return_value = True

            await tool_execution_node(state)

        assert captured_priority.get("priority") == "Medium", (
            f"Low confidence should set Medium priority. "
            f"Got: {captured_priority.get('priority')}"
        )

    @pytest.mark.asyncio
    async def test_ticket_always_created_regardless_of_confidence(self):
        """Ticket must be created even for very low confidence."""
        from app.agents.workflow import tool_execution_node

        for confidence in [0.10, 0.45, 0.74, 0.75, 0.90]:
            state = {
                "user_request":    "Analyze failure",
                "root_cause":      "Some root cause",
                "recommendation":  "Some recommendation",
                "logs":            "ERROR some error",
                "confidence_score": confidence,
                "low_confidence":  confidence < 0.75
            }

            tickets_created = []

            with patch("app.tools.jira_tool.create_jira_ticket") as mock_jira, \
                 patch("app.tools.slack_tool.send_incident_notification") as mock_slack:

                async def capture_jira(title, description, priority):
                    tickets_created.append(title)
                    return f"SCRUM-{int(confidence * 100)}"

                mock_jira.side_effect  = capture_jira
                mock_slack.return_value = True

                await tool_execution_node(state)

            assert len(tickets_created) == 1, (
                f"Ticket must always be created. "
                f"Confidence {confidence} — tickets created: {len(tickets_created)}"
            )