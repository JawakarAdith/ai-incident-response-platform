import pytest

# ── Reusable test fixtures ─────────────────────────────────

@pytest.fixture
def clear_logs():
    return """
[2024-01-15 02:28:41] ERROR DatabaseConnectionPool: Connection timeout after 30s
[2024-01-15 02:28:41] ERROR Pool size: 100/100 connections exhausted
[2024-01-15 02:28:42] FATAL Payment service crashed
"""

@pytest.fixture
def vague_logs():
    return """
[2024-01-15 03:00:00] ERROR Something failed
[2024-01-15 03:00:01] ERROR Unknown error occurred
[2024-01-15 03:00:02] ERROR Service unavailable
"""

@pytest.fixture
def memory_logs():
    return """
[2024-01-15 04:15:22] ERROR java.lang.OutOfMemoryError: Java heap space
[2024-01-15 04:15:23] FATAL Order service crashed - insufficient memory
[2024-01-15 04:15:24] ERROR GC overhead limit exceeded
"""

@pytest.fixture
def cascade_logs():
    return """
[2024-01-15 06:00:01] ERROR Auth service: Redis connection refused on port 6379
[2024-01-15 06:00:02] ERROR User service: Cannot connect to auth service
[2024-01-15 06:00:03] FATAL Redis server crashed - out of memory 4096MB/4096MB
[2024-01-15 06:00:04] ERROR 234 requests failed in last 60 seconds
"""

@pytest.fixture
def strong_root_cause():
    return "Database connection pool exhausted. PostgreSQL max_connections limit reached."

@pytest.fixture
def weak_root_cause():
    return "Something went wrong with the service. Error occurred."

@pytest.fixture
def strong_recommendation():
    return (
        "Increase connection pool size from 100 to 300. "
        "Restart payment service. Add connection timeout retry logic."
    )

@pytest.fixture
def weak_recommendation():
    return "Check the service and restart if needed."

@pytest.fixture
def rag_context():
    return """
PAST SIMILAR INCIDENTS:
Past Incident 1 (92% similar):
Problem: DB connection pool exhausted
Fix that worked: Increased max_connections to 500
"""