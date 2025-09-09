# -*- coding: utf-8 -*-
"""
Entry Agent Tools - 파이프라인 단계별 도구

각 Agent의 메서드를 Tool로 래핑하여 EntryAgent에서 사용
"""
import logging
from typing import Dict

from langchain_core.tools import tool

from app.agent.query_analyzer_agent import get_query_analyzer_agent
from app.agent.query_planning_agent import get_query_planning_agent
from app.agent.executor_agent import get_executor_agent
from app.agent.script_agent import get_script_agent
from app.schemas.query_plan import QueryPlan
from app.schemas.plan_result import PlanResult

logger = logging.getLogger(__name__)


# ==================== Tool Functions ====================

@tool
def analyze_query(query: str) -> Dict:
    """
    사용자의 자연어 쿼리를 분석하여 NormalizedQuery로 변환합니다.

    Args:
        query: 사용자의 자연어 쿼리

    Returns:
        NormalizedQuery dict
    """
    logger.info(f"[Tool] analyze_query: {query}")
    analyzer = get_query_analyzer_agent()
    return analyzer.analyze(query)


@tool
def make_plan(normalized_query: Dict) -> Dict:
    """
    NormalizedQuery를 기반으로 실행 계획(QueryPlan)을 생성합니다.

    Args:
        normalized_query: NormalizedQuery dict

    Returns:
        QueryPlan dict
    """
    logger.info(f"[Tool] make_plan: {normalized_query.get('intent_type')}")
    planner = get_query_planning_agent()
    plan = planner.make_plan(normalized_query)
    return plan.model_dump()


@tool
def execute_plan(plan_dict: Dict, original_query: str) -> Dict:
    """
    QueryPlan을 실행하여 데이터를 수집하고 요약합니다.

    Args:
        plan_dict: QueryPlan dict
        original_query: 사용자 원본 쿼리

    Returns:
        PlanResult dict
    """
    logger.info(f"[Tool] execute_plan: {plan_dict.get('intent_type')}")
    executor = get_executor_agent()
    plan = QueryPlan(**plan_dict)
    result = executor.do_plan(plan, original_query)
    return result.model_dump()


@tool
def generate_script(result_dict: Dict) -> str:
    """
    PlanResult를 기반으로 최종 사용자 응답을 생성합니다.

    Args:
        result_dict: PlanResult dict

    Returns:
        최종 응답 문자열
    """
    logger.info(f"[Tool] generate_script")
    script_agent = get_script_agent()
    result = PlanResult(**result_dict)
    return script_agent.generate(result)


# ==================== Direct Call Functions ====================
# LangChain tool 없이 직접 호출용

def call_analyze_query(query: str) -> Dict:
    """analyze_query 직접 호출"""
    analyzer = get_query_analyzer_agent()
    return analyzer.analyze(query)


def call_make_plan(normalized_query: Dict) -> Dict:
    """make_plan 직접 호출"""
    planner = get_query_planning_agent()
    plan = planner.make_plan(normalized_query)
    return plan.model_dump()


def call_execute_plan(plan_dict: Dict, original_query: str) -> Dict:
    """execute_plan 직접 호출"""
    executor = get_executor_agent()
    plan = QueryPlan(**plan_dict)
    result = executor.do_plan(plan, original_query)
    return result.model_dump()


def call_generate_script(result_dict: Dict) -> str:
    """generate_script 직접 호출"""
    script_agent = get_script_agent()
    result = PlanResult(**result_dict)
    return script_agent.generate(result)


# ==================== Full Pipeline ====================

def run_full_pipeline(query: str) -> Dict:
    """
    전체 파이프라인 실행

    Args:
        query: 사용자 쿼리

    Returns:
        {
            "response": str,
            "normalized_query": Dict,
            "plan_result": Dict
        }
    """
    normalized_query = call_analyze_query(query)
    plan_dict = call_make_plan(normalized_query)
    result_dict = call_execute_plan(plan_dict, query)
    response = call_generate_script(result_dict)

    return {
        "response": response,
        "normalized_query": normalized_query,
        "plan_result": result_dict
    }
