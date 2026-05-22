import uuid
from typing import Optional
from app.memory.chroma_client import get_incidents_collection
from app.memory.embeddings import get_embedding


async def store_incident(
    problem: str,
    root_cause: str,
    fix: str,
    service: str = "unknown",
    jira_ticket: str = None,
    confidence: float = 0.0
) -> str:
    """
    Store resolved incident in ChromaDB.
    
    Args:
        problem: what went wrong
        root_cause: why it happened
        fix: what fixed it
        service: affected service name
        jira_ticket: related Jira ticket
        confidence: confidence score
    
    Returns:
        incident ID
    """
    collection = get_incidents_collection()
    
    # Combine problem + fix into one document
    document = f"""
Problem: {problem}
Root Cause: {root_cause}
Fix that worked: {fix}
Service: {service}
    """.strip()
    
    # Generate unique ID
    incident_id = str(uuid.uuid4())
    
    # Convert document to vector
    embedding = get_embedding(document)
    
    # Store in ChromaDB
    collection.add(
        ids=[incident_id],
        documents=[document],
        embeddings=[embedding],
        metadatas=[{
            "service": service,
            "jira_ticket": jira_ticket or "none",
            "confidence": str(confidence),
            "fixed": "true"
        }]
    )
    
    print(f"✅ Incident stored in RAG: {incident_id}")
    return incident_id


async def search_similar_incidents(
    problem: str,
    n_results: int = 3
) -> list:
    """
    Search for similar past incidents.
    
    Args:
        problem: current problem description
        n_results: number of results to return
    
    Returns:
        list of similar incidents with fixes
    """
    collection = get_incidents_collection()
    
    # Check if collection has any entries
    if collection.count() == 0:
        print("📭 No past incidents in RAG memory")
        return []
    
    # Convert problem to vector
    embedding = get_embedding(problem)
    
    # Search for similar incidents
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"]
    )
    
    # Format results
    similar_incidents = []
    for i, doc in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        similarity = 1 - distance  # convert distance to similarity
        
        # Only return if similarity > 50%
        if similarity > 0.5:
            similar_incidents.append({
                "document": doc,
                "similarity": round(similarity, 2),
                "metadata": results["metadatas"][0][i]
            })
            print(f"✅ Found similar incident: {similarity:.0%} match")
    
    return similar_incidents


async def get_rag_context(problem: str) -> str:
    """
    Get RAG context for a problem.
    Returns formatted string to inject into agent prompt.
    
    Args:
        problem: current problem
    
    Returns:
        formatted context string
    """
    similar = await search_similar_incidents(problem)
    
    if not similar:
        return ""
    
    context = "PAST SIMILAR INCIDENTS (use these as reference):\n"
    context += "─" * 50 + "\n"
    
    for i, incident in enumerate(similar, 1):
        context += f"\nPast Incident {i} ({incident['similarity']:.0%} similar):\n"
        context += incident["document"]
        context += f"\nJira: {incident['metadata'].get('jira_ticket', 'N/A')}"
        context += "\n" + "─" * 50 + "\n"
    
    return context


async def pre_feed_incidents():
    """
    Pre-feed known incidents into RAG memory.
    Call this once to populate RAG with known fixes.
    """
    collection = get_incidents_collection()
    
    # Skip if already populated
    if collection.count() > 0:
        print(f"📦 RAG already has {collection.count()} incidents")
        return
    
    print("🔄 Pre-feeding incidents into RAG memory...")
    
    known_incidents = [
        {
            "problem": "DB connection pool exhausted service crashed",
            "root_cause": "max_connections limit reached on PostgreSQL",
            "fix": "Increased max_connections from 100 to 500 in postgresql.conf and restarted DB",
            "service": "payment-service"
        },
        {
            "problem": "Memory leak OutOfMemoryError Java heap space",
            "root_cause": "Unclosed database connections accumulating over time",
            "fix": "Restarted service, fixed connection leak in code, added connection timeout",
            "service": "order-service"
        },
        {
            "problem": "Disk space full storage service stopped",
            "root_cause": "Old log files accumulating on /data partition",
            "fix": "Cleaned old logs, set up log rotation, increased disk size",
            "service": "storage-service"
        },
        {
            "problem": "API gateway timeout upstream service unavailable",
            "root_cause": "Auth service crashed due to high load",
            "fix": "Restarted auth service, added auto-scaling, increased replicas to 3",
            "service": "api-gateway"
        },
        {
            "problem": "High CPU usage service slow response",
            "root_cause": "Inefficient database query causing full table scan",
            "fix": "Added database index on frequently queried columns, query optimized",
            "service": "user-service"
        }
    ]
    
    for incident in known_incidents:
        await store_incident(
            problem=incident["problem"],
            root_cause=incident["root_cause"],
            fix=incident["fix"],
            service=incident["service"],
            confidence=0.95
        )
    
    print(f"✅ Pre-fed {len(known_incidents)} incidents into RAG memory!")


async def add_memory(
    problem: str,
    solution: str,
    tags: str = ""
):
    """
    Wrapper for API memory feed endpoint
    """

    incident_id = await store_incident(
        problem=problem,
        root_cause="Manual memory feed",
        fix=solution,
        service=tags or "manual",
        confidence=0.95
    )

    return {
        "incident_id": incident_id,
        "status": "stored"
    }


async def search_memory(query: str):
    """
    Wrapper for API memory search endpoint
    """

    results = await search_similar_incidents(query)

    return results