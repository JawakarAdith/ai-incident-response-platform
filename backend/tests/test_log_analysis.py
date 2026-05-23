import pytest
from unittest.mock import AsyncMock, patch


class TestLogAnalysis:
    """
    Tests for log analysis agent.
    Mocks the LLM to test our logic, not Groq's API.
    """

    @pytest.mark.asyncio
    async def test_detects_db_connection_issue(self, clear_logs):
        """Should identify database/connection as root cause."""
        with patch("app.agents.log_analysis.llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=type(
                "Response", (), {
                    "content": (
                        "Root cause: Database connection pool exhausted. "
                        "PostgreSQL max_connections limit of 100 reached."
                    )
                }
            )())

            from app.agents.log_analysis import run_log_analysis
            result = await run_log_analysis(
                logs=clear_logs,
                plan="Analyze deployment failure"
            )

        result_lower = result.lower()
        assert any(
            keyword in result_lower
            for keyword in ["connection", "database", "pool", "postgres"]
        ), f"Expected DB-related root cause, got: {result}"

    @pytest.mark.asyncio
    async def test_detects_memory_issue(self, memory_logs):
        """Should identify memory/heap as root cause."""
        with patch("app.agents.log_analysis.llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=type(
                "Response", (), {
                    "content": (
                        "Root cause: Java heap space exhausted. "
                        "OutOfMemoryError indicates memory leak in order service."
                    )
                }
            )())

            from app.agents.log_analysis import run_log_analysis
            result = await run_log_analysis(
                logs=memory_logs,
                plan="Analyze order service crash"
            )

        result_lower = result.lower()
        assert any(
            keyword in result_lower
            for keyword in ["memory", "heap", "outofmemory", "leak"]
        ), f"Expected memory-related root cause, got: {result}"

    @pytest.mark.asyncio
    async def test_cascade_failure_finds_redis_root(self, cascade_logs):
        """
        Multiple services failing — should identify Redis
        as root cause, not downstream effects.
        """
        with patch("app.agents.log_analysis.llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=type(
                "Response", (), {
                    "content": (
                        "Root cause: Redis server crashed due to memory exhaustion "
                        "(4096MB/4096MB). Auth, user, and order service failures "
                        "are downstream effects."
                    )
                }
            )())

            from app.agents.log_analysis import run_log_analysis
            result = await run_log_analysis(
                logs=cascade_logs,
                plan="Analyze production outage"
            )

        assert "redis" in result.lower(), (
            f"Expected Redis as root cause for cascade failure, got: {result}"
        )

    @pytest.mark.asyncio
    async def test_handles_empty_logs_gracefully(self):
        """Empty logs should not crash — should return generic message."""
        with patch("app.agents.log_analysis.llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=type(
                "Response", (), {
                    "content": "No logs provided. Unable to determine root cause."
                }
            )())

            from app.agents.log_analysis import run_log_analysis
            result = await run_log_analysis(logs="", plan="Analyze issue")

        assert result is not None
        assert len(result) > 0, "Should return some response even for empty logs"