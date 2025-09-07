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

SEMANTIC_QUERY_SYSTEM_PROMPT = """당신은 암호화폐 뉴스 벡터DB 검색을 위한 키워드 생성 전문가입니다.

[역할]
주어진 파라미터를 분석하여 벡터 DB 시맨틱 검색에 최적화된 **키워드 조합**을 생성합니다.

[파라미터 설명]
- coin_names: 검색 대상 코인 심볼 (BTC, ETH 등)
- intent_type: 검색 의도
  - market_trend: 시장 동향, 가격 추세 관련
  - price_reason: 가격 변동 원인, 호재/악재 분석
  - news_summary: 일반 뉴스, 소식, 이슈
- event_magnitude: 이벤트 강도
  - surge: 급등, 상승 관련
  - plunge: 급락, 하락 관련
  - any: 특정 방향 없음
- event_keywords: 특정 이벤트 키워드 (규제, ETF, 해킹 등)
- custom_context: 추가 컨텍스트

[키워드 생성 규칙 - 중요]
1. **오직 키워드만** 출력 (문장 형태 금지)
2. 조사, 접속사, 불필요한 수식어 제외
3. 코인 심볼 + 핵심 명사/동사만 사용
4. 3-8개의 키워드를 공백으로 구분
5. 한글과 영어 키워드 혼용 가능

[좋은 예시]
- BTC 비트코인 급등 ETF 승인 기관투자
- ETH 이더리움 하락 SEC 규제 소송
- BTC 가격 상승 반감기 채굴 난이도

[나쁜 예시 - 이렇게 하지 마세요]
- "비트코인이 급등한 이유를 알아보기 위한 검색" (문장 형태)
- "BTC의 가격이 상승했습니다" (조사 포함)

[출력]
공백으로 구분된 키워드만 출력하세요. 설명, 따옴표, 문장 없이 키워드만."""


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
    similarity_threshold: float = 0.7,
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
        similarity_threshold: 유사도 임계값 0~1 (기본값: 0.7)
        pivot_date: 기준 날짜 (epoch timestamp, 00:00:00). None이면 날짜 필터 없음
        date_range: 날짜 범위 ("day", "week", "month"). pivot_date와 함께 사용
        source: 뉴스 출처 필터

    Returns:
        검색된 뉴스 리스트

    Examples:
        # make_semantic_query와 함께 사용
        query = make_semantic_query(coin_names=["BTC"], intent_type="price_reason")
        semantic_search(query, top_k=15, similarity_threshold=0.65)

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


# ==================== Query Extractor from News ====================

QUERY_EXTRACTOR_SYSTEM_PROMPT = """당신은 암호화폐 뉴스 벡터DB 검색을 위한 키워드 추출 전문가입니다.

[역할]
뉴스 제목과 본문을 분석하여 연관된 **키워드 조합**들을 추출합니다.

[분석 관점]
1. 핵심 주제: 코인명, 이벤트명, 인물명
2. 연관 이벤트: 관련된 다른 사건이나 배경
3. 원인/결과: 원인이 되는 사건, 예상되는 영향
4. 관련 코인: 직접 언급된 코인 외 연관된 코인들
5. 시장 맥락: 거시경제, 규제, 기술적 요인

[키워드 생성 규칙 - 중요]
1. **오직 키워드만** 출력 (문장 형태 금지)
2. 조사(이, 가, 를, 에 등) 절대 사용 금지
3. 접속사, 수식어 제외
4. 핵심 명사만 추출 (3-6개 키워드/줄)
5. 3-7줄의 서로 다른 키워드 조합 생성
6. 한글과 영어 키워드 혼용 가능

[좋은 예시]
BTC ETF 승인 SEC 블랙록
비트코인 기관투자 그레이스케일 펀드
암호화폐 금리 인하 연준 유동성

[나쁜 예시 - 이렇게 하지 마세요]
"비트코인이 급등한 이유" (조사 포함, 문장 형태)
"SEC의 ETF 승인에 대한 시장 반응" (조사 포함)

[출력 형식]
각 키워드 조합을 줄바꿈으로 구분.
설명, 번호, 따옴표 없이 키워드만 출력."""


@traceable(name="QueryExtractor.extract", run_type="llm")
def _extract_queries_from_content(title: str, document: str) -> List[str]:
    """
    LLM을 사용하여 뉴스 콘텐츠에서 연관 쿼리 추출

    LangSmith에서 추적:
    - Input: 뉴스 제목, 본문
    - Output: 추출된 쿼리 리스트
    """
    llm = _get_query_generator_llm()

    user_prompt = f"""다음 뉴스를 분석하여 연관된 검색 쿼리들을 생성하세요:

[제목]
{title}

[본문]
{document}

위 뉴스와 연관된 다양한 관점의 검색 쿼리들을 생성하세요."""

    messages = [
        {"role": "system", "content": QUERY_EXTRACTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response = llm.invoke(messages)

    # 줄바꿈으로 분리하여 리스트로 변환
    queries = [q.strip() for q in response.content.strip().split('\n') if q.strip()]
    return queries


@tool
def extract_queries_from_news(
    title: str,
    document: str
) -> List[str]:
    """
    VectorNewsResult의 title과 document를 분석하여 연관 검색 쿼리 리스트를 생성합니다.
    LLM이 뉴스 콘텐츠를 분석하여 다양한 관점의 추가 검색 쿼리를 생성합니다.

    Args:
        title: 뉴스 제목
        document: 뉴스 본문/요약

    Returns:
        연관 검색 쿼리 문자열 리스트 (3-7개)

    Examples:
        # VectorNewsResult에서 쿼리 추출
        news = semantic_search("BTC ETF", top_k=1)[0]
        queries = extract_queries_from_news(news.title, news.document)
        # → ["BTC ETF SEC 승인 규제", "비트코인 기관투자 유입", "암호화폐 시장 전망 분석", ...]
    """
    try:
        if not title and not document:
            logger.warning("Both title and document are empty")
            return []

        # 빈 값 처리
        title = title or ""
        document = document or ""

        queries = _extract_queries_from_content(title, document)

        logger.info(f"Extracted {len(queries)} queries from news")
        return queries

    except Exception as e:
        logger.error(f"Failed to extract queries from news: {e}")
        return []
