# -*- coding: utf-8 -*-
"""Agent Router - Independent endpoints for each agent"""
import os
import logging
from fastapi import APIRouter, Query, HTTPException, Depends

from app.agent.query_analyzer_agent import QueryAnalyzerService
from app.agent.query_planning_agent import QueryPlanningAgent
from app.agent.executor_agent import ExecutorAgent
from app.schemas.normalized_query import NormalizedQuery
from app.schemas.query_plan import QueryPlan

logger = logging.getLogger(__name__)

agent_router = APIRouter(prefix="/agent", tags=["agent"])


# ==================== 1. Query Analyzer Agent ====================

@agent_router.post("/analyze")
def analyze_query(
    query: str = Query(..., description="Natural language query to analyze"),
    service: QueryAnalyzerService = Depends(QueryAnalyzerService)
):
    """
    [Layer 1] Query Analyzer Agent

    Converts natural language query to structured NormalizedQuery JSON.

    - Input: Natural language (e.g., "BTC 10월 이슈 분석해줘")
    - Output: NormalizedQuery (intent_type, target, time_range, etc.)
    """
    try:
        logger.info(f"[QueryAnalyzer] Input: {query}")
        result = service.analyze_query(query)
        logger.info(f"[QueryAnalyzer] Output: {result}")
        return {
            "status": "success",
            "agent": "query_analyzer",
            "input": query,
            "output": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[QueryAnalyzer] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query analysis failed: {str(e)}")


# ==================== 2. Query Planning Agent ====================

@agent_router.post("/plan")
def create_query_plan(
    query: str = Query(..., description="Natural language query to plan"),
    query_analyzer: QueryAnalyzerService = Depends(QueryAnalyzerService),
    query_planner: QueryPlanningAgent = Depends(QueryPlanningAgent)
):
    """
    [Layer 2] Query Planning Agent

    Maps NormalizedQuery to DB tool calls (QueryPlan).

    - Input: Natural language query (internally calls QueryAnalyzer first)
    - Output: QueryPlan (query_plan with mapped tool calls)
    """
    try:
        # Debug: 환경변수 확인
        logger.info(f"[LangSmith] LANGCHAIN_TRACING_V2={os.getenv('LANGCHAIN_TRACING_V2')}")
        logger.info(f"[LangSmith] LANGCHAIN_PROJECT={os.getenv('LANGCHAIN_PROJECT')}")

        # Step 1: Analyze query
        logger.info(f"[QueryPlanner] Input: {query}")
        normalized_query = query_analyzer.analyze_query(query)
        logger.info(f"[QueryPlanner] Normalized: {normalized_query}")

        # Step 2: Create plan
        query_plan = query_planner.make_plan(normalized_query)
        logger.info(f"[QueryPlanner] Plan created with {len(query_plan.query_plan)} tool calls")

        return {
            "status": "success",
            "agent": "query_planner",
            "input": query,
            "normalized_query": normalized_query,
            "output": query_plan.model_dump(),
            "_debug_langsmith": {
                "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
                "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT"),
                "LANGCHAIN_API_KEY_SET": bool(os.getenv("LANGCHAIN_API_KEY"))
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QueryPlanner] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query planning failed: {str(e)}")


@agent_router.post("/plan/from-json")
def create_query_plan_from_json(
    normalized_query: NormalizedQuery,
    query_planner: QueryPlanningAgent = Depends(QueryPlanningAgent)
):
    """
    [Layer 2] Query Planning Agent (Direct JSON input)

    Maps NormalizedQuery JSON directly to QueryPlan.

    - Input: NormalizedQuery JSON body
    - Output: QueryPlan
    """
    try:
        logger.info(f"[QueryPlanner] Direct JSON input: {normalized_query}")

        query_plan = query_planner.make_plan(normalized_query.model_dump())
        logger.info(f"[QueryPlanner] Plan created with {len(query_plan.query_plan)} tool calls")

        return {
            "status": "success",
            "agent": "query_planner",
            "input": normalized_query.model_dump(),
            "output": query_plan.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QueryPlanner] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query planning failed: {str(e)}")


# ==================== 3. Executor Agent ====================

@agent_router.post("/execute")
def execute_plan(
    query: str = Query(..., description="Natural language query to execute"),
    query_analyzer: QueryAnalyzerService = Depends(QueryAnalyzerService),
    query_planner: QueryPlanningAgent = Depends(QueryPlanningAgent),
    executor: ExecutorAgent = Depends(ExecutorAgent)
):
    """
    [Layer 3] Executor Agent

    Executes QueryPlan by calling database tools and collecting results.

    - Input: Natural language query (internally calls QueryAnalyzer + QueryPlanner first)
    - Output: PlanResult (collected prices, news, execution stats)
    """
    try:
        # Step 1: Analyze query
        logger.info(f"[Executor] Input: {query}")
        normalized_query = query_analyzer.analyze_query(query)

        # Step 2: Create plan
        query_plan = query_planner.make_plan(normalized_query)
        logger.info(f"[Executor] Executing {len(query_plan.query_plan)} tool calls")

        # Step 3: Execute plan
        plan_result = executor.do_plan(query_plan)
        logger.info(f"[Executor] Result: {plan_result.successful_actions}/{plan_result.total_actions} successful")

        return {
            "status": "success",
            "agent": "executor",
            "input": query,
            "normalized_query": normalized_query,
            "query_plan": query_plan.model_dump(),
            "output": plan_result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Executor] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@agent_router.post("/execute/from-plan")
def execute_from_plan(
    query_plan: QueryPlan,
    executor: ExecutorAgent = Depends(ExecutorAgent)
):
    """
    [Layer 3] Executor Agent (Direct QueryPlan input)

    Executes QueryPlan directly from JSON body.

    - Input: QueryPlan JSON body
    - Output: PlanResult
    """
    try:
        logger.info(f"[Executor] Direct QueryPlan input with {len(query_plan.query_plan)} tool calls")

        plan_result = executor.do_plan(query_plan)
        logger.info(f"[Executor] Result: {plan_result.successful_actions}/{plan_result.total_actions} successful")

        return {
            "status": "success",
            "agent": "executor",
            "input": query_plan.model_dump(),
            "output": plan_result.model_dump()
        }
    except Exception as e:
        logger.error(f"[Executor] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


# ==================== 4. Full Chain ====================

@agent_router.post("/chain")
def run_full_chain(
    query: str = Query(..., description="Natural language query to process"),
    query_analyzer: QueryAnalyzerService = Depends(QueryAnalyzerService),
    query_planner: QueryPlanningAgent = Depends(QueryPlanningAgent),
    executor: ExecutorAgent = Depends(ExecutorAgent)
):
    """
    [Full Chain] All Agents in sequence

    Runs complete pipeline: QueryAnalyzer -> QueryPlanner -> Executor

    Returns all intermediate results for debugging.
    """
    try:
        logger.info(f"[Chain] Starting full chain for: {query}")

        # Layer 1: Query Analysis
        normalized_query = query_analyzer.analyze_query(query)

        # Layer 2: Query Planning
        query_plan = query_planner.make_plan(normalized_query)

        # Layer 3: Execution
        plan_result = executor.do_plan(query_plan)

        logger.info(f"[Chain] Completed: {plan_result.successful_actions}/{plan_result.total_actions}")

        return {
            "status": "success",
            "agent": "full_chain",
            "input": query,
            "layer_1_query_analyzer": normalized_query,
            "layer_2_query_planner": query_plan.model_dump(),
            "layer_3_executor": plan_result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chain] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chain execution failed: {str(e)}")


# ==================== Debug ====================

@agent_router.get("/debug/langsmith")
def debug_langsmith():
    """LangSmith 환경변수 확인"""
    return {
        "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
        "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT"),
        "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY", "")[:25] + "..." if os.getenv("LANGCHAIN_API_KEY") else None
    }
