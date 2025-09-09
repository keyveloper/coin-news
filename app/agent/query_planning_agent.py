# -*- coding: utf-8 -*-
"""
Query Planning Agent - LLM 기반 다중 쿼리 계획 생성

역할:
1. NormalizedQuery 분석
2. LLM이 적절한 도구 호출 계획 생성
3. QueryPlan 반환 (Executor가 순차 실행)
"""
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langsmith import traceable

from app.schemas.query_plan import QueryPlan, QueryPlanOutput, ToolCall

logger = logging.getLogger(__name__)


# ==================== Prompt Loading ====================

def _load_prompt(filename: str) -> str:
    """app/prompt 디렉토리에서 프롬프트 파일 로드"""
    prompt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt")
    prompt_path = os.path.join(prompt_dir, filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


PLANNER_SYSTEM_PROMPT = _load_prompt("query_planning_agent_system_prompt")


# ==================== Depth/Range Mappings ====================

DEPTH_PARAMS = {
    "short": {"top_k": 10, "similarity_threshold": 0.1},
    "medium": {"top_k": 15, "similarity_threshold": 0.0},
    "deep": {"top_k": 25, "similarity_threshold": -0.2},
}

RELATIVE_TO_RANGE = {
    "24h": "day",
    "7d": "week",
    "1m": "month",
    "ytd": "year",
    "all": "year",
}


class QueryPlanningAgent:
    """Query Planning Agent - LLM 기반 쿼리 계획 생성"""

    _instance: Optional["QueryPlanningAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.model_name = os.getenv("ANTHROPIC_PLANNER_MODEL", "claude-3-5-haiku-20241022")
        self.temperature = float(os.getenv("PLANNER_TEMPERATURE", "0.0"))
        self.timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "30.0"))

        self._initialized = True
        logger.info(f"QueryPlanningAgent initialized with model: {self.model_name}")

    def _get_llm(self) -> ChatAnthropic:
        """LLM 인스턴스 반환"""
        return ChatAnthropic(
            model_name=self.model_name,
            temperature=self.temperature,
            timeout=self.timeout,
            max_tokens=1024
        )

    def _calculate_pivot_time(self, normalized_query: Dict) -> int:
        """NormalizedQuery의 time_range에서 pivot_time 계산"""
        pivot_time_str = normalized_query.get("time_range", {}).get("pivot_time")

        if pivot_time_str == "today" or pivot_time_str is None:
            now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            return int(now.timestamp())

        try:
            dt = datetime.strptime(str(pivot_time_str), "%Y%m%d")
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            return int(now.timestamp())

    @traceable(name="QueryPlanner.plan", run_type="llm")
    def make_plan(self, normalized_query: Dict) -> QueryPlan:
        """
        NormalizedQuery를 분석하여 QueryPlan 생성

        Args:
            normalized_query: NormalizedQuery dict

        Returns:
            QueryPlan with ToolCalls
        """
        logger.info(f"Planning query: {normalized_query}")

        intent_type = normalized_query.get("intent_type", "unknown")
        if intent_type == "unknown":
            raise ValueError("Unknown intent type")

        # Extract data
        target = normalized_query.get("target", {})
        coin_names = target.get("coin", ["BTC"])

        event = normalized_query.get("event", {})
        event_magnitude = event.get("magnitude")
        base_keywords = event.get("keywords", [])

        goal = normalized_query.get("goal", {})
        depth = goal.get("depth", "medium")

        time_range = normalized_query.get("time_range", {})
        relative = time_range.get("relative", "1m")

        pivot_time = self._calculate_pivot_time(normalized_query)

        # LLM call
        llm = self._get_llm()
        llm_with_tools = llm.bind_tools([QueryPlanOutput], tool_choice="QueryPlanOutput")

        user_prompt = f"""다음 NormalizedQuery에 대한 데이터 수집 계획을 생성하세요:

intent_type: {intent_type}
coins: {coin_names}
keywords: {base_keywords}
magnitude: {event_magnitude}
depth: {depth}
time_range: {relative}

적절한 검색 관점과 키워드를 선택하여 QueryPlanOutput 도구를 호출하세요."""

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        response = llm_with_tools.invoke(messages)

        # Extract plan from tool call
        if not response.tool_calls:
            raise ValueError("No tool call in response")

        plan_output = response.tool_calls[0]["args"]
        logger.info(f"LLM generated plan: {plan_output}")

        # Convert to QueryPlan
        query_plan: List[ToolCall] = []

        # Add price query if needed
        if plan_output.get("include_price_data", False):
            range_type = plan_output.get("price_range_type", RELATIVE_TO_RANGE.get(relative, "month"))
            direction = plan_output.get("price_direction", "both")

            for coin in coin_names:
                query_plan.append(ToolCall(
                    tool_name="get_coin_price",
                    arguments={
                        "coin_name": coin,
                        "pivot_date": pivot_time,
                        "range_type": range_type,
                        "direction": direction
                    }
                ))

        # Add semantic queries
        depth_params = DEPTH_PARAMS.get(depth, DEPTH_PARAMS["medium"])
        magnitude_map = {"big": "surge", "small": "plunge"}
        tool_magnitude = magnitude_map.get(event_magnitude, "any") if event_magnitude else None

        for sq in plan_output.get("semantic_queries", []):
            # Combine base keywords with query-specific keywords
            combined_keywords = list(set(base_keywords + sq.get("event_keywords", [])))

            query_plan.append(ToolCall(
                tool_name="make_semantic_query",
                arguments={
                    "coin_names": coin_names,
                    "intent_type": intent_type,
                    "event_keywords": combined_keywords,
                    "event_magnitude": tool_magnitude,
                    "custom_context": sq.get("search_perspective", ""),
                    "_search_params": {
                        "top_k": depth_params["top_k"],
                        "similarity_threshold": depth_params["similarity_threshold"],
                        "pivot_date": pivot_time,
                        "date_range": RELATIVE_TO_RANGE.get(relative, "month")
                    }
                }
            ))

        logger.info(f"Generated {len(query_plan)} tool calls")

        return QueryPlan(
            intent_type=intent_type,
            pivot_time=pivot_time,
            query_plan=query_plan
        )


def get_query_planning_agent() -> QueryPlanningAgent:
    """QueryPlanningAgent 싱글톤 인스턴스 반환"""
    return QueryPlanningAgent()
