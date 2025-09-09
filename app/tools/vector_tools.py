# -*- coding: utf-8 -*-
"""
Vector Tools - 시맨틱 뉴스 검색 도구

1. make_semantic_query: LLM 기반 검색 쿼리 생성
2. semantic_search: 쿼리 문자열로 뉴스 검색
3. extract_queries_from_news: 뉴스 콘텐츠에서 연관 쿼리 추출
"""
import os
import logging
from typing import List, Optional, Literal
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langsmith import traceable
from app.repository.news_repository import NewsRepository
from app.schemas.vector_news import VectorNewsResult

logger = logging.getLogger(__name__)


# ==================== Semantic Query Generator ====================

SEMANTIC_QUERY_SYSTEM_PROMPT = """암호화폐 뉴스 검색용 키워드 생성기.

규칙:
- 키워드만 출력 (문장 금지)
- 3-8개 키워드, 공백 구분
- 코인 심볼 + 핵심 명사만

예시: BTC 비트코인 급등 ETF 승인 기관투자"""


def _get_query_generator_llm():
    """쿼리 생성용 LLM 인스턴스 반환"""
    model_name = os.getenv("ANTHROPIC_QUERY_GENERATOR_MODEL_NAME", "claude-3-5-haiku-20241022")
    temperature = float(os.getenv("TEMPERATURE", "0.0"))
    timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "30.0"))

    return ChatAnthropic(
        model_name=model_name,
        temperature=temperature,
        timeout=timeout,
        stop=None
    )


@traceable(name="SemanticQueryGenerator.generate", run_type="llm")
def _generate_semantic_query(
    coin_names: List[str],
    intent_type: str,
    event_magnitude: Optional[str],
    event_keywords: Optional[List[str]],
    custom_context: Optional[str]
) -> str:
    """
    LLM을 사용하여 시맨틱 검색 쿼리 생성

    LangSmith에서 추적:
    - Input: coin_names, intent_type, event_magnitude 등
    - Output: 생성된 쿼리 문자열
    - LLM이 어떤 키워드를 선택했는지 확인 가능
    """
    llm = _get_query_generator_llm()

    user_prompt = f"""다음 파라미터를 분석하여 시맨틱 검색 쿼리를 생성하세요:

coin_names: {coin_names}
intent_type: {intent_type}
event_magnitude: {event_magnitude if event_magnitude else "없음"}
event_keywords: {event_keywords if event_keywords else "없음"}
custom_context: {custom_context if custom_context else "없음"}

위 정보를 바탕으로 뉴스 검색에 적합한 쿼리 문자열을 생성하세요."""

    messages = [
        {"role": "system", "content": SEMANTIC_QUERY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response = llm.invoke(messages)
    return response.content.strip()


@tool
def make_semantic_query(
    coin_names: List[str],
    intent_type: Literal["market_trend", "price_reason", "news_summary"],
    event_keywords: Optional[List[str]] = None,
    event_magnitude: Optional[Literal["surge", "plunge", "any"]] = None,
    custom_context: Optional[str] = None
) -> str:
    """
    NormalizedQuery 필드를 분석하여 semantic_search에 사용할 쿼리 문자열을 생성합니다.
    LLM이 파라미터를 분석하여 최적의 시맨틱 검색 쿼리를 생성합니다.

    Args:
        coin_names: 코인 심볼 리스트 (예: ["BTC", "ETH"])
        intent_type: 의도 유형 (market_trend, price_reason, news_summary)
        event_keywords: 이벤트 관련 키워드 리스트 (예: ["규제", "승인"])
        event_magnitude: 이벤트 강도 (surge, plunge, any)
        custom_context: 추가 컨텍스트 문자열

    Returns:
        생성된 시맨틱 검색 쿼리 문자열
    """
    try:
        # LangSmith에서 추적되는 헬퍼 함수 호출
        query = _generate_semantic_query(
            coin_names=coin_names,
            intent_type=intent_type,
            event_magnitude=event_magnitude,
            event_keywords=event_keywords,
            custom_context=custom_context
        )

        logger.info(f"LLM generated semantic query: {query}")
        return query

    except Exception as e:
        logger.error(f"Failed to generate semantic query: {e}")
        # Fallback: 기본 키워드 조합
        fallback_parts = coin_names.copy()
        if event_keywords:
            fallback_parts.extend(event_keywords)
        return " ".join(fallback_parts)


@tool
def semantic_search(
    query: str,
    top_k: int = 10,
    similarity_threshold: float = 0.0,
    pivot_date: Optional[int] = None,
    date_range: Optional[Literal["day", "week", "month"]] = None,
    source: Optional[str] = None
) -> List[VectorNewsResult]:
    """
    시맨틱 뉴스 검색 - 쿼리 문자열로 관련 뉴스를 검색합니다.

    make_semantic_query로 생성한 쿼리를 사용하거나 직접 쿼리를 전달합니다.

    Args:
        query: 검색할 쿼리 문자열 (make_semantic_query 결과 또는 직접 입력)
        top_k: 반환할 최대 결과 개수 (기본값: 10)
        similarity_threshold: 유사도 임계값 (기본값: 0.0). L2 distance 사용시 낮은 값 권장
        pivot_date: 기준 날짜 (epoch timestamp, 00:00:00). None이면 날짜 필터 없음
        date_range: 날짜 범위 ("day", "week", "month"). pivot_date와 함께 사용
        source: 뉴스 출처 필터

    Returns:
        검색된 뉴스 리스트

    Examples:
        # make_semantic_query와 함께 사용
        query = make_semantic_query(coin_names=["BTC"], intent_type="price_reason")
        semantic_search(query, top_k=15, similarity_threshold=0.1)

        # 직접 쿼리 사용
        semantic_search("BTC 가격 상승 원인", top_k=10)
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
