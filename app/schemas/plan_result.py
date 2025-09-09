"""Plan Result Schema for Executor Agent

역할: 가격 데이터 분석/요약, 뉴스 데이터 수집/요약 후 다음 레이어에 전달
- Raw 데이터는 전달하지 않고 요약만 전달
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

    combined_summary: Optional[str] = Field(
        default=None,
        description="LLM-generated combined analysis of price and news"
    )

    # 추가 생성 쿼리 (뉴스에서 추출)
    generated_queries: List[str] = Field(
        default_factory=list,
        description="Additional queries extracted from news for further search"
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
                "combined_summary": "[종합 분석] 가격 상승과 ETF 뉴스 상관관계...",
                "generated_queries": ["BTC ETF SEC", "비트코인 기관투자"],
                "total_actions": 6,
                "successful_actions": 6,
                "failed_actions": 0,
                "errors": []
            }
        }
