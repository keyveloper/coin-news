import logging
from fastapi import APIRouter, Query, HTTPException, Depends
from app.services.rag_service import RAGService
from app.agent.task_planning_agent import TaskPlanningAgent
from app.agent.query_analyzer_agent import QueryAnalyzerService

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

@bot_route.post("/agent")
def plan(
        query: str = Query(..., description="User query to analyze"),
        query_analyzer_service: QueryAnalyzerService = Depends(QueryAnalyzerService),
        task_planning_agent: TaskPlanningAgent = Depends(TaskPlanningAgent)
):
    try:
        logger.info(f"Received query: {query}")

        # query to json
        jsoned_query = query_analyzer_service.analyze_query(query)

        # make plan
        plan = task_planning_agent.make_plan(jsoned_query)

        return {
            "plan": plan
        }



    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in query analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
