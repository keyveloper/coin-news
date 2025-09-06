# -*- coding: utf-8 -*-
"""
Vector Tools - 시맨틱 뉴스 검색 도구

NewsRepository.search를 호출하여 뉴스 검색 수행
(embedding 변환은 repository 내부에서 처리)
"""
import logging
from typing import List, Optional, Literal
from langchain.tools import tool
from app.repository.news_repository import NewsRepository
from app.schemas.vector_news import VectorNewsResult

logger = logging.getLogger(__name__)


@tool
def semantic_search(
    query: str,
    top_k: int = 10,
    similarity_threshold: float = 0.7,
    pivot_date: Optional[int] = None,
    date_range: Optional[Literal["day", "week", "month"]] = None,
    source: Optional[str] = None
) -> List[VectorNewsResult]:
    """
    시맨틱 뉴스 검색 - 쿼리 문자열로 관련 뉴스를 검색합니다.

    QueryPlanningAgent가 NormalizedQuery를 분석하여 파라미터를 조합합니다:
    - query: coin_name + intent_keywords + context 조합
    - top_k: goal.depth에 따라 결정 (short: 10, medium: 15, deep: 25)
    - similarity_threshold: goal.depth에 따라 결정 (short: 0.75, medium: 0.65, deep: 0.55)
    - pivot_date: time_range.pivot_time (특정 날짜 필터링 시)
    - date_range: 날짜 범위 (day, week, month)

    Args:
        query: 검색할 쿼리 문자열 (예: "BTC 가격 상승 규제 기관 투자")
        top_k: 반환할 최대 결과 개수 (기본값: 10)
        similarity_threshold: 유사도 임계값 0~1 (기본값: 0.7)
        pivot_date: 기준 날짜 (epoch timestamp, 00:00:00). None이면 날짜 필터 없음
        date_range: 날짜 범위 ("day", "week", "month"). pivot_date와 함께 사용
        source: 뉴스 출처 필터

    Returns:
        검색된 뉴스 리스트

    Examples:
        # 기본 검색 (날짜 필터 없음)
        semantic_search("BTC 가격 상승 원인 규제", top_k=15, similarity_threshold=0.65)

        # 특정 날짜 하루 검색
        semantic_search("ETH DeFi 업데이트", top_k=10, pivot_date=1727740800)

        # 날짜 범위 검색 (pivot_date 기준 ±7일)
        semantic_search("XRP 규제", pivot_date=1727740800, date_range="week")
    """
    try:
        logger.info(f"semantic_search: query={query}, top_k={top_k}, pivot_date={pivot_date}")

        repo = NewsRepository()
        results = repo.search(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            pivot_date=pivot_date,
            date_range=date_range,
            source=source
        )

        logger.info(f"Found {len(results)} news articles")
        return results

    except Exception as e:
        logger.error(f"semantic_search failed: {e}")
        return []
