from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.core.security import decode_token
from app.memory.rag_service import add_memory, search_memory

router = APIRouter(prefix="/memory", tags=["memory"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class FeedRequest(BaseModel):
    problem:  str
    solution: str
    tags:     Optional[str] = ""


class SearchRequest(BaseModel):
    query: str


@router.post("/feed")
async def feed_memory(
    request: FeedRequest,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Feed a past incident into RAG memory."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not request.problem or not request.solution:
        raise HTTPException(
            status_code=400,
            detail="Both problem and solution are required."
        )

    try:
        result = await add_memory(
            problem=request.problem,
            solution=request.solution,
            tags=request.tags or ""
        )
        return {
            "status":      "stored",
            "incident_id": result["incident_id"],
            "message":     "Saved to RAG memory successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_rag_memory(
    request: SearchRequest,
    token: str = Depends(oauth2_scheme)
):
    """Search past incidents in RAG memory."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not request.query:
        raise HTTPException(status_code=400, detail="Query is required.")

    try:
        raw_results = await search_memory(request.query)

        # Format for frontend
        formatted = []
        for item in raw_results:
            # Parse the stored document back into fields
            doc   = item.get("document", "")
            meta  = item.get("metadata", {})
            score = item.get("similarity", 0)

            # Extract problem and solution from document text
            lines    = doc.split("\n")
            problem  = ""
            solution = ""
            for line in lines:
                if line.startswith("Problem:"):
                    problem = line.replace("Problem:", "").strip()
                elif line.startswith("Fix that worked:"):
                    solution = line.replace("Fix that worked:", "").strip()

            formatted.append({
                "problem":  problem  or doc[:200],
                "solution": solution or "See full document",
                "tags":     meta.get("service", ""),
                "score":    f"{score:.0%}",
                "jira":     meta.get("jira_ticket", "N/A")
            })

        return {"results": formatted, "count": len(formatted)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count")
async def get_memory_count(
    token: str = Depends(oauth2_scheme)
):
    """How many incidents are stored in RAG memory."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        from app.memory.chroma_client import get_incidents_collection
        collection = get_incidents_collection()
        return {"count": collection.count()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))