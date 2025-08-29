import logging
from fastapi import APIRouter, Query, HTTPException
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

bot_route = APIRouter(prefix="/bot", tags=["bot"])


@bot_route.post("/query")
def query_analysis(
    query: str = Query(..., description="User query to analyze")
):
    try:
        logger.info(f"Received query: {query}")

        # Initialize RAG service
        rag_service = RAGService()

        # Execute make_script to perform analysis
        result = rag_service.make_script(query)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in query analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")