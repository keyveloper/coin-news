import logging
from fastapi import APIRouter, Query, HTTPException, Depends
from app.services.rag_service import RAGService
from app.agent.task_planning_agent import TaskPlanningAgent
from app.agent.query_analyzer_agent import QueryAnalyzerService
from app.agent.executor_agent import ExecutorAgent

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


@bot_route.post("/chain")
def chain(
        query: str = Query(..., description="User query to process through agent chain"),
        query_analyzer_service: QueryAnalyzerService = Depends(QueryAnalyzerService),
        task_planning_agent: TaskPlanningAgent = Depends(TaskPlanningAgent),
        executor_agent: ExecutorAgent = Depends(ExecutorAgent)
):
    """
    Agent Chain Orchestration Endpoint

    Processes user query through multiple agent layers:
    1. QueryAnalyzerAgent: Natural language → NormalizedQuery (JSON)
    2. TaskPlanningAgent: NormalizedQuery → TaskPlan (execution plan)
    3. ExecutorAgent: TaskPlan → Actual data from DB
    4. (Future) ResponseAgent: Data + instructions → Final answer

    Currently returns execution results for development/debugging.
    """
    try:
        logger.info(f"[CHAIN] Starting agent chain for query: {query}")

        # Layer 1: Query Analysis
        logger.info("[CHAIN] Layer 1: Analyzing query...")
        normalized_query = query_analyzer_service.analyze_query(query)
        logger.info(f"[CHAIN] Normalized query: {normalized_query}")

        # Layer 2: Task Planning
        logger.info("[CHAIN] Layer 2: Generating task plan...")
        task_plan = task_planning_agent.make_plan(normalized_query)
        logger.info(f"[CHAIN] Task plan created with {len(task_plan.action_plan)} actions")

        # Layer 3: Execute Plan
        logger.info("[CHAIN] Layer 3: Executing task plan...")
        plan_result = executor_agent.do_plan(task_plan)
        logger.info(f"[CHAIN] Execution completed: {plan_result.successful_actions}/{plan_result.total_actions} successful")

        # TODO: Layer 4 - ResponseAgent (generate final answer)

        return {
            "status": "success",
            "current_layer": "execution",
            "normalized_query": normalized_query,
            "task_plan": task_plan.model_dump(),
            "plan_result": plan_result.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAIN] Error in agent chain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent chain error: {str(e)}")
