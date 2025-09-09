"""Plan Result Schema for Executor Agent

역할: 가격 데이터 분석/요약, 뉴스 데이터 수집/요약 후 다음 레이어에 전달
- Raw 데이터는 전달하지 않고 요약만 전달
- Combined summary는 다음 레이어에서 생성
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class PlanResult(BaseModel):
    """Result of executing a QueryPlan - 다음 레이어로 전달되는 요약 결과"""

    # 원본 쿼리 (QueryPlanningAgent 검증용)
    original_query: str = Field(
        description="User's original query for verification"
    )

    intent_type: str = Field(
        description="Intent type from QueryPlan (price_reason, market_trend, news_summary)"
    )

    # 대상 코인
    coin_names: List[str] = Field(
        default_factory=list,
        description="List of coins that were analyzed"
    )

    # LLM 생성 요약 (다음 레이어로 전달)
    price_summary: Optional[str] = Field(
        default=None,
        description="LLM-generated summary of price data analysis"
    )

    news_summary: Optional[str] = Field(
        default=None,
        description="LLM-generated summary of collected news"
    )

    # 실행 통계
    total_actions: int = Field(description="Total number of tool calls executed")
    successful_actions: int = Field(description="Number of successful tool calls")
    failed_actions: int = Field(description="Number of failed tool calls")

    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages if any tools failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "10월 중순 비트코인 급등 원인",
                "intent_type": "price_reason",
                "coin_names": ["BTC"],
                "price_summary": "BTC 10월 +15% 상승. 주요 저항선 $70,000 돌파...",
                "news_summary": "[주요 이슈] ETF 승인 임박 + 기관투자 유입...",
                "total_actions": 6,
                "successful_actions": 6,
                "failed_actions": 0,
                "errors": []
            }
        }
