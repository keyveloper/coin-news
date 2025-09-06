# -*- coding: utf-8 -*-
"""
Query Planning Agent - NormalizedQuery를 분석하여 DB tool 호출 계획 생성

역할:
1. NormalizedQuery 데이터 분석
2. 등록된 DB tools 확인
3. tools 파라미터에 맞게 NormalizedQuery 데이터를 매핑
4. QueryPlan으로 결과 반환
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from app.schemas.query_plan import QueryPlan, ToolCall
from datetime import datetime, timezone

# Register DB tools
from app.tools.price_tools import get_coin_price
from app.tools.vector_tools import semantic_search


class QueryPlanningAgent:
    """
    Query Planning Agent that maps NormalizedQuery to DB tool calls.

    Pipeline:
    1. Receive NormalizedQuery from QueryAnalyzerAgent
    2. Analyze intent_type, target, time_range, goal
    3. Map data to registered tool parameters
    4. Return QueryPlan with tool call specifications

    Available Tools:
    - get_coin_price: 가격 데이터 조회
    - semantic_search: 시맨틱 뉴스 검색 (query string 기반)
    """
    _instance: Optional["QueryPlanningAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # LLM setup
        model_name = os.getenv("ANTHROPIC_QUERY_PLANNER_MODEL_NAME", "claude-3-5-haiku-20241022")
        temperature = float(os.getenv("TEMPERATURE", "0.0"))
        timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "60.0"))

        self.llm = ChatAnthropic(
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            stop=None
        )

        # Load system prompt
        prompt_dir = Path(__file__).parent.parent / "prompt"
        prompt_file = prompt_dir / "query_planning_agent_system_prompt"
        self.system_prompt = prompt_file.read_text(encoding="utf-8")

        # Registered DB tools
        # - get_coin_price: 통합 가격 조회 tool
        # - semantic_search: 통합 시맨틱 뉴스 검색 tool
        self.tools = [
            get_coin_price,
            semantic_search,
        ]

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        self._initialized = True

    def make_plan(self, normalized_query: Dict) -> QueryPlan:
        """
        NormalizedQuery를 분석하여 QueryPlan 생성.

        Process:
        1. NormalizedQuery 데이터 분석 (intent_type, target, time_range, goal)
        2. 등록된 tools의 파라미터 확인
        3. NormalizedQuery → tool arguments 매핑
        4. QueryPlan 반환

        :param normalized_query: NormalizedQuery as dict
        :return: QueryPlan with mapped tool calls
        :raises: HTTPException if intent_type is "unknown"
        """
        # Check for unknown intention
        if normalized_query.get("intent_type") == "unknown":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "UNKNOWN_INTENT",
                    "message": "Unable to determine user intent. Query analysis failed.",
                    "suggestion": "Please rephrase your query with clearer intent"
                }
            )

        # Calculate pivot_time from NormalizedQuery
        pivot_time = self._calculate_pivot_time(normalized_query)

        # Create messages for LLM
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Analyze this NormalizedQuery and generate a QueryPlan:

{json.dumps(normalized_query, indent=2, ensure_ascii=False)}

**Calculated pivot_time**: {pivot_time} (epoch timestamp at 00:00:00)

Map the NormalizedQuery data to appropriate tool parameters:
- target.coin → coin_name
- time_range.relative → range_type mapping
- intent_type → direction logic
- pivot_time → pivot_date

Call the tools with correctly mapped parameters.
"""}
        ]

        # Invoke LLM with tools
        response = self.llm_with_tools.invoke(messages)

        # Extract tool calls and map to QueryPlan
        query_plan = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                query_plan.append(ToolCall(
                    tool_name=tool_call["name"],
                    arguments=tool_call["args"]
                ))

        return QueryPlan(
            intent_type=normalized_query["intent_type"],
            pivot_time=pivot_time,
            query_plan=query_plan
        )

    def _calculate_pivot_time(self, normalized_query: Dict) -> int:
        """
        NormalizedQuery의 time_range에서 pivot_time 계산.

        :param normalized_query: NormalizedQuery dict
        :return: epoch timestamp (00:00:00)
        """
        pivot_time_str = normalized_query.get("time_range", {}).get("pivot_time")

        if pivot_time_str == "today" or pivot_time_str is None:
            # Current date at 00:00:00 UTC
            now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            return int(now.timestamp())

        # Parse date string (YYYYMMDD format)
        try:
            dt = datetime.strptime(str(pivot_time_str), "%Y%m%d")
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            # Fallback to today
            now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            return int(now.timestamp())


def get_query_planning_agent() -> QueryPlanningAgent:
    """QueryPlanningAgent 싱글톤 인스턴스 반환"""
    return QueryPlanningAgent()
