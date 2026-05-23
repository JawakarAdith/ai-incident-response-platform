import pytest
from unittest.mock import patch, MagicMock


class TestRagService:

    @pytest.mark.asyncio
    async def test_store_and_retrieve_incident(self):
        """Store an incident then search — should find it."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 1
        mock_collection.query.return_value = {
            "documents": [["Problem: DB connection pool exhausted\nFix that worked: Increase connections"]],
            "metadatas": [[{"service": "payment", "jira_ticket": "SCRUM-1"}]],
            "distances": [[0.05]]   # low distance = high similarity
        }

        with patch("app.memory.rag_service.get_incidents_collection",
                   return_value=mock_collection), \
             patch("app.memory.rag_service.get_embedding",
                   return_value=[0.1] * 384):

            from app.memory.rag_service import search_similar_incidents
            results = await search_similar_incidents(
                "database connection pool exhausted payment service"
            )

        assert len(results) > 0, "Should find similar incident"
        assert results[0]["similarity"] >= 0.5, (
            f"Similarity should be high for similar problem. "
            f"Got: {results[0]['similarity']}"
        )

    @pytest.mark.asyncio
    async def test_empty_collection_returns_no_results(self):
        """Empty RAG memory should return empty list, not crash."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0

        with patch("app.memory.rag_service.get_incidents_collection",
                   return_value=mock_collection):

            from app.memory.rag_service import search_similar_incidents
            results = await search_similar_incidents("database crash")

        assert results == [], "Empty collection should return empty list"

    @pytest.mark.asyncio
    async def test_low_similarity_results_filtered_out(self):
        """Results below 50% similarity should be excluded."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 1
        mock_collection.query.return_value = {
            "documents": [["Problem: Something completely unrelated"]],
            "metadatas": [[{"service": "unknown"}]],
            "distances": [[0.60]]   # high distance = low similarity (0.40)
        }

        with patch("app.memory.rag_service.get_incidents_collection",
                   return_value=mock_collection), \
             patch("app.memory.rag_service.get_embedding",
                   return_value=[0.1] * 384):

            from app.memory.rag_service import search_similar_incidents
            results = await search_similar_incidents("database crash")

        assert results == [], (
            "Low similarity results should be filtered out"
        )