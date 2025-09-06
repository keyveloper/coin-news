"""Vector News Schema - ChromaDB 뉴스 검색 결과 스키마"""
from typing import Optional
from pydantic import BaseModel, Field


class VectorNewsResult(BaseModel):
    """
    NewsRepository에서 반환하는 뉴스 검색 결과 스키마

    find_news_by_semantic_query(), find_by_semantic_query_with_one_day_range() 결과 형식
    """
    title: Optional[str] = Field(None, description="뉴스 제목")
    url: Optional[str] = Field(None, description="뉴스 URL (find_news_by_semantic_query)")
    link: Optional[str] = Field(None, description="뉴스 링크 (find_by_semantic_query_with_one_day_range)")
    created_at: Optional[str] = Field(None, description="생성 시간 (ISO format)")
    publish_date: Optional[int] = Field(None, description="발행 날짜 (epoch timestamp)")
    publish_date_readable: Optional[str] = Field(None, description="발행 날짜 (읽기 쉬운 형식)")
    source: Optional[str] = Field(None, description="뉴스 출처")
    query: Optional[str] = Field(None, description="검색 쿼리")
    distance: Optional[float] = Field(None, description="벡터 거리 (작을수록 유사)")
    similarity_score: Optional[float] = Field(None, description="유사도 점수 (1 - distance)")
    document: Optional[str] = Field(None, description="뉴스 본문/요약")


class VectorNewsBasic(BaseModel):
    """
    find_all_news() 결과 형식 - 간단한 뉴스 목록
    """
    title: Optional[str] = Field(None, description="뉴스 제목")
    url: Optional[str] = Field(None, description="뉴스 URL")
    created_at: Optional[str] = Field(None, description="생성 시간 (ISO format)")