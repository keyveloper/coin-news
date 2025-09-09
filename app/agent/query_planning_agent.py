# -*- coding: utf-8 -*-
"""
Query Planning Agent - NormalizedQuery를 분석하여 다중 쿼리 계획 생성

역할:
1. NormalizedQuery 데이터 분석
2. intent_type에 따라 다양한 관점의 쿼리 생성
3. 규칙 기반으로 여러 make_semantic_query 호출 계획
4. QueryPlan으로 결과 반환 (Executor가 순차 실행)
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import HTTPException
from langsmith import traceable
from app.schemas.query_plan import QueryPlan, ToolCall
from datetime import datetime, timezone


# 관점별 쿼리 생성 템플릿
QUERY_PERSPECTIVES = {
    "price_reason": [
        {"custom_context": "직접적인 가격 변동 원인", "event_keywords": ["급등", "급락", "상승", "하락"]},
        {"custom_context": "시장 환경 및 거시경제 영향", "event_keywords": ["시장", "금리", "달러", "유동성"]},
        {"custom_context": "호재 이벤트 분석", "event_keywords": ["ETF", "승인", "기관투자", "채택"]},
        {"custom_context": "규제 및 정책 변화", "event_keywords": ["규제", "SEC", "정책", "법안"]},
        {"custom_context": "기술적 요인 분석", "event_keywords": ["반감기", "채굴", "해시레이트", "네트워크"]},
    ],
    "market_trend": [
        {"custom_context": "전반적인 시장 동향", "event_keywords": ["시장", "추세", "동향"]},
        {"custom_context": "거래량 및 투자자 동향", "event_keywords": ["거래량", "투자자", "매수", "매도"]},
        {"custom_context": "기관 및 대형 투자자 움직임", "event_keywords": ["기관", "고래", "대량"]},
    ],
    "news_summary": [
        {"custom_context": "주요 뉴스 이슈", "event_keywords": ["뉴스", "소식", "발표"]},
        {"custom_context": "프로젝트 업데이트", "event_keywords": ["업데이트", "개발", "로드맵"]},
        {"custom_context": "파트너십 및 협력", "event_keywords": ["파트너십", "협력", "제휴"]},
        {"custom_context": "거래소 관련 소식", "event_keywords": ["거래소", "상장", "입출금"]},
    ],
}

# goal.depth에 따른 semantic_search 파라미터
# Note: L2 distance 사용으로 similarity score가 낮음. threshold 낮게 설정
DEPTH_PARAMS = {
    "short": {"top_k": 10, "similarity_threshold": 0.1},
    "medium": {"top_k": 15, "similarity_threshold": 0.0},
    "deep": {"top_k": 25, "similarity_threshold": -0.2},
}

# time_range.relative → range_type 매핑
RELATIVE_TO_RANGE = {
    "24h": "day",
    "7d": "week",
    "1m": "month",
    "ytd": "year",
    "all": "year",
}


class QueryPlanningAgent:
    """
    Query Planning Agent - 규칙 기반 다중 쿼리 계획 생성

    Pipeline:
    1. NormalizedQuery 분석
    2. intent_type에 따라 다양한 관점의 쿼리 템플릿 선택
    3. 각 관점에 대해 make_semantic_query ToolCall 생성
    4. get_coin_price ToolCall 추가 (가격 분석 필요시)
    5. QueryPlan 반환

    Note: semantic_search는 Executor에서 make_semantic_query 결과로 자동 호출됨
    """
    _instance: Optional["QueryPlanningAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

    @traceable(name="QueryPlanner.make_plan", run_type="chain")
    def make_plan(self, normalized_query: Dict) -> QueryPlan:
        """
        NormalizedQuery를 분석하여 다중 쿼리 QueryPlan 생성.

        Args:
            normalized_query: NormalizedQuery dict

        Returns:
            QueryPlan with multiple ToolCalls
        """
        # Check for unknown intention
        intent_type = normalized_query.get("intent_type", "unknown")
        if intent_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "UNKNOWN_INTENT",
                    "message": "Unable to determine user intent.",
                    "suggestion": "Please rephrase your query with clearer intent"
                }
            )

        # Extract data from NormalizedQuery
        target = normalized_query.get("target", {})
        coin_names = target.get("coin", ["BTC"])

        event = normalized_query.get("event", {})
        event_magnitude = event.get("magnitude")
        base_keywords = event.get("keywords", [])

        goal = normalized_query.get("goal", {})
        depth = goal.get("depth", "medium")

        time_range = normalized_query.get("time_range", {})
        relative = time_range.get("relative", "1m")

        # Calculate pivot_time
        pivot_time = self._calculate_pivot_time(normalized_query)

        # Build query plan
        query_plan: List[ToolCall] = []

        # Step 1: Add get_coin_price (for price-related intents)
        if intent_type in ["price_reason", "market_trend"]:
            range_type = RELATIVE_TO_RANGE.get(relative, "month")
            direction = "both" if intent_type == "price_reason" else "before"

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

        # Step 2: Add multiple make_semantic_query calls (다양한 관점)
        perspectives = QUERY_PERSPECTIVES.get(intent_type, QUERY_PERSPECTIVES["news_summary"])
        depth_params = DEPTH_PARAMS.get(depth, DEPTH_PARAMS["medium"])

        # Map event_magnitude to tool parameter
        magnitude_map = {"big": "surge", "small": "plunge"}
        tool_magnitude = magnitude_map.get(event_magnitude, "any") if event_magnitude else None

        for perspective in perspectives:
            # 관점별 키워드와 기본 키워드 결합
            combined_keywords = list(set(base_keywords + perspective["event_keywords"]))

            query_plan.append(ToolCall(
                tool_name="make_semantic_query",
                arguments={
                    "coin_names": coin_names,
                    "intent_type": intent_type,
                    "event_keywords": combined_keywords,
                    "event_magnitude": tool_magnitude,
                    "custom_context": perspective["custom_context"],
                    # Executor에서 사용할 메타데이터
                    "_search_params": {
                        "top_k": depth_params["top_k"],
                        "similarity_threshold": depth_params["similarity_threshold"],
                        "pivot_date": pivot_time,
                        "date_range": RELATIVE_TO_RANGE.get(relative, "month")
                    }
                }
            ))

        return QueryPlan(
            intent_type=intent_type,
            pivot_time=pivot_time,
            query_plan=query_plan
        )

    def _calculate_pivot_time(self, normalized_query: Dict) -> int:
        """NormalizedQuery의 time_range에서 pivot_time 계산."""
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


def get_query_planning_agent() -> QueryPlanningAgent:
    """QueryPlanningAgent 싱글톤 인스턴스 반환"""
    return QueryPlanningAgent()
