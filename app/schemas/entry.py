from typing import List, Dict, Optional

from pydantic import BaseModel, Field
# ==================== Tool Definitions ====================


class AnalyzeQueryInput(BaseModel):
    """analyze_query 도구 입력"""
    query: str = Field(description="사용자의 자연어 쿼리")


class MakePlanInput(BaseModel):
    """make_plan 도구 입력"""
    normalized_query: Dict = Field(description="NormalizedQuery dict")


class ExecutePlanInput(BaseModel):
    """execute_plan 도구 입력"""
    # QueryPlan을 dict로 받아서 처리
    intent_type: str = Field(description="intent_type")
    pivot_time: int = Field(description="pivot_time")
    query_plan: List[Dict] = Field(description="tool calls list")
    original_query: str = Field(description="사용자 원본 쿼리")


class GenerateScriptInput(BaseModel):
    """generate_script 도구 입력"""
    original_query: str = Field(description="사용자 원본 쿼리")
    intent_type: str = Field(description="분석 유형")
    coin_names: List[str] = Field(description="코인 목록")
    price_summary: Optional[str] = Field(default=None, description="가격 요약")
    news_summary: Optional[str] = Field(default=None, description="뉴스 요약")


class DirectResponseInput(BaseModel):
    """직접 응답 도구 입력"""
    response: str = Field(description="사용자에게 직접 전달할 응답")


# ==================== Entry Agent ====================
