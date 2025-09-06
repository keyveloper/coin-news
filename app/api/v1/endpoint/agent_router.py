# -*- coding: utf-8 -*-
"""Agent Router - Independent endpoints for each agent"""
import logging
from fastapi import APIRouter, Query, HTTPException, Depends

from app.agent.query_analyzer_agent import QueryAnalyzerService
from app.agent.task_planning_agent import TaskPlanningAgent
from app.agent.executor_agent import ExecutorAgent
from app.schemas.normalized_query import NormalizedQuery
from app.schemas.task_plan import TaskPlan

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


# ==================== 2. Task Planning Agent ====================

@agent_router.post("/plan")
def create_task_plan(
    query: str = Query(..., description="Natural language query to plan"),
    query_analyzer: QueryAnalyzerService = Depends(QueryAnalyzerService),
    task_planner: TaskPlanningAgent = Depends(TaskPlanningAgent)
):
    """
    [Layer 2] Task Planning Agent

    Generates execution plan (TaskPlan) from NormalizedQuery.

    - Input: Natural language query (internally calls QueryAnalyzer first)
    - Output: TaskPlan (action_plan with tool calls, analysis_instructions)
    """
    try:
        # Step 1: Analyze query
        logger.info(f"[TaskPlanner] Input: {query}")
        normalized_query = query_analyzer.analyze_query(query)
        logger.info(f"[TaskPlanner] Normalized: {normalized_query}")

        # Step 2: Create plan
        task_plan = task_planner.make_plan(normalized_query)
        logger.info(f"[TaskPlanner] Plan created with {len(task_plan.action_plan)} actions")

        return {
            "status": "success",
            "agent": "task_planner",
            "input": query,
            "normalized_query": normalized_query,
            "output": task_plan.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TaskPlanner] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Task planning failed: {str(e)}")


@agent_router.post("/plan/from-json")
def create_task_plan_from_json(
    normalized_query: NormalizedQuery,
    task_planner: TaskPlanningAgent = Depends(TaskPlanningAgent)
):
    """
    [Layer 2] Task Planning Agent (Direct JSON input)

    Generates execution plan directly from NormalizedQuery JSON.

    - Input: NormalizedQuery JSON body
    - Output: TaskPlan
    """
    try:
        logger.info(f"[TaskPlanner] Direct JSON input: {normalized_query}")

        task_plan = task_planner.make_plan(normalized_query.model_dump())
        logger.info(f"[TaskPlanner] Plan created with {len(task_plan.action_plan)} actions")

        return {
            "status": "success",
            "agent": "task_planner",
            "input": normalized_query.model_dump(),
            "output": task_plan.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TaskPlanner] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Task planning failed: {str(e)}")


# ==================== 3. Executor Agent ====================

@agent_router.post("/execute")
def execute_plan(
    query: str = Query(..., description="Natural language query to execute"),
    query_analyzer: QueryAnalyzerService = Depends(QueryAnalyzerService),
    task_planner: TaskPlanningAgent = Depends(TaskPlanningAgent),
    executor: ExecutorAgent = Depends(ExecutorAgent)
):
    """
    [Layer 3] Executor Agent

    Executes TaskPlan by calling database tools and collecting results.

    - Input: Natural language query (internally calls QueryAnalyzer + TaskPlanner first)
    - Output: PlanResult (collected prices, news, execution stats)
    """
    try:
        # Step 1: Analyze query
        logger.info(f"[Executor] Input: {query}")
        normalized_query = query_analyzer.analyze_query(query)

        # Step 2: Create plan
        task_plan = task_planner.make_plan(normalized_query)
        logger.info(f"[Executor] Executing {len(task_plan.action_plan)} actions")

        # Step 3: Execute plan
        plan_result = executor.do_plan(task_plan)
        logger.info(f"[Executor] Result: {plan_result.successful_actions}/{plan_result.total_actions} successful")

        return {
            "status": "success",
            "agent": "executor",
            "input": query,
            "normalized_query": normalized_query,
            "task_plan": task_plan.model_dump(),
            "output": plan_result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Executor] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@agent_router.post("/execute/from-plan")
def execute_from_plan(
    task_plan: TaskPlan,
    executor: ExecutorAgent = Depends(ExecutorAgent)
):
    """
    [Layer 3] Executor Agent (Direct TaskPlan input)

    Executes TaskPlan directly from JSON body.

    - Input: TaskPlan JSON body
    - Output: PlanResult
    """
    try:
        logger.info(f"[Executor] Direct TaskPlan input with {len(task_plan.action_plan)} actions")

        plan_result = executor.do_plan(task_plan)
        logger.info(f"[Executor] Result: {plan_result.successful_actions}/{plan_result.total_actions} successful")

        return {
            "status": "success",
            "agent": "executor",
            "input": task_plan.model_dump(),
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
    task_planner: TaskPlanningAgent = Depends(TaskPlanningAgent),
    executor: ExecutorAgent = Depends(ExecutorAgent)
):
    """
    [Full Chain] All Agents in sequence

    Runs complete pipeline: QueryAnalyzer -> TaskPlanner -> Executor

    Returns all intermediate results for debugging.
    """
    try:
        logger.info(f"[Chain] Starting full chain for: {query}")

        # Layer 1: Query Analysis
        normalized_query = query_analyzer.analyze_query(query)

        # Layer 2: Task Planning
        task_plan = task_planner.make_plan(normalized_query)

        # Layer 3: Execution
        plan_result = executor.do_plan(task_plan)

        logger.info(f"[Chain] Completed: {plan_result.successful_actions}/{plan_result.total_actions}")

        return {
            "status": "success",
            "agent": "full_chain",
            "input": query,
            "layer_1_query_analyzer": normalized_query,
            "layer_2_task_planner": task_plan.model_dump(),
            "layer_3_executor": plan_result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chain] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chain execution failed: {str(e)}")
