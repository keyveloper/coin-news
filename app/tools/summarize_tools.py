# -*- coding: utf-8 -*-
"""
Summarization Tools for Executor Agent

1. summarize_price_data: 가격 데이터 요약
2. summarize_news_chunks: 뉴스 청크들 요약
"""
import os
import logging
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langsmith import traceable

from app.schemas.price import PriceData, PriceHourlyData
from app.schemas.vector_news import VectorNewsResult

logger = logging.getLogger(__name__)


def _get_summarizer_llm():
    """요약용 LLM 인스턴스 반환"""
    model_name = os.getenv("ANTHROPIC_SUMMARIZER_MODEL_NAME", "claude-3-5-haiku-20241022")
    temperature = float(os.getenv("SUMMARIZER_TEMPERATURE", "0.0"))
    timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "60.0"))

    return ChatAnthropic(
        model_name=model_name,
        temperature=temperature,
        timeout=timeout,
        max_tokens=2048,
        stop=None
    )


# ==================== Price Data Summarization ====================

PRICE_SUMMARY_SYSTEM_PROMPT = """당신은 암호화폐 가격 데이터 분석 전문가입니다.

[역할]
주어진 가격 데이터를 분석하여 핵심 인사이트를 추출합니다.

[분석 항목]
1. 가격 추세: 상승/하락/횡보
2. 변동폭: 최고가, 최저가, 변동률
3. 주요 변곡점: 급등/급락 시점
4. 거래량 패턴 (있는 경우)

[출력 형식]
간결한 키워드 중심의 요약 (3-5문장)
- 핵심 수치 포함
- 투자자 관점의 인사이트

예시:
"BTC 10월 중순 기준 1개월간 +15.3% 상승. 10/5 급등 시작점($62,000→$71,000).
주요 저항선 $70,000 돌파 후 안착. 거래량 평균 대비 2.3배 증가."
"""


@traceable(name="Summarizer.price_data", run_type="llm")
def _summarize_price_internal(
    coin_name: str,
    price_data: List[Dict[str, Any]],
    analysis_focus: Optional[str] = None
) -> str:
    """LLM을 사용하여 가격 데이터 요약"""
    llm = _get_summarizer_llm()

    # 가격 데이터 포맷팅
    if not price_data:
        return f"{coin_name}: 가격 데이터 없음"

    # 가격 통계 계산
    prices = [p.get("close", p.get("price", 0)) for p in price_data if p.get("close") or p.get("price")]
    if not prices:
        return f"{coin_name}: 유효한 가격 데이터 없음"

    high = max(prices)
    low = min(prices)
    first = prices[0]
    last = prices[-1]
    change_pct = ((last - first) / first * 100) if first > 0 else 0

    # 데이터 샘플링 (너무 길면 일부만 사용)
    sample_data = price_data[:20] if len(price_data) > 20 else price_data

    user_prompt = f"""다음 {coin_name} 가격 데이터를 분석하여 요약하세요:

[통계 요약]
- 기간: {len(price_data)}개 데이터 포인트
- 시작가: ${first:,.2f}
- 종가: ${last:,.2f}
- 최고가: ${high:,.2f}
- 최저가: ${low:,.2f}
- 변동률: {change_pct:+.2f}%

[샘플 데이터]
{sample_data}

{f"[분석 초점]: {analysis_focus}" if analysis_focus else ""}

핵심 인사이트를 3-5문장으로 요약하세요."""

    messages = [
        {"role": "system", "content": PRICE_SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response = llm.invoke(messages)
    return response.content.strip()


@tool
def summarize_price_data(
    coin_name: str,
    price_data: List[Dict[str, Any]],
    analysis_focus: Optional[str] = None
) -> str:
    """
    가격 데이터를 분석하여 핵심 인사이트를 추출합니다.

    Args:
        coin_name: 코인 심볼 (BTC, ETH 등)
        price_data: 가격 데이터 리스트 (PriceData 또는 PriceHourlyData의 dict 형태)
        analysis_focus: 분석 초점 (예: "급등 원인", "변동성 분석")

    Returns:
        가격 분석 요약 문자열

    Examples:
        summary = summarize_price_data(
            coin_name="BTC",
            price_data=[{"date": "2025-10-15", "close": 71000, ...}, ...],
            analysis_focus="10월 급등 원인"
        )
    """
    try:
        if not price_data:
            return f"{coin_name}: 가격 데이터가 없습니다."

        summary = _summarize_price_internal(coin_name, price_data, analysis_focus)
        logger.info(f"Price summary generated for {coin_name}: {len(summary)} chars")
        return summary

    except Exception as e:
        error_msg = f"가격 데이터 요약 실패 ({coin_name}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# ==================== News Data Summarization ====================

NEWS_SUMMARY_SYSTEM_PROMPT = """당신은 암호화폐 뉴스 분석 전문가입니다.

[역할]
여러 뉴스 청크(chunk)들을 분석하여 핵심 내용을 요약합니다.

[분석 항목]
1. 주요 이슈: 가장 중요한 뉴스 토픽
2. 시장 영향: 호재/악재 판단
3. 관련 키워드: 핵심 키워드 추출
4. 시간순 정리: 이벤트 타임라인

[출력 형식]
구조화된 요약 (5-10문장):
- 핵심 이슈별 정리
- 시장 영향 분석
- 주요 키워드 나열

예시:
"[주요 이슈] SEC ETF 승인 임박 소식 + 기관투자 유입 증가
[시장 영향] 강한 호재 - 단기 상승 모멘텀 형성
[키워드] ETF, SEC, BlackRock, 기관투자, 규제완화
[타임라인] 10/10 ETF 신청 → 10/12 SEC 검토 시작 → 10/15 승인 기대감"
"""


@traceable(name="Summarizer.news_chunks", run_type="llm")
def _summarize_news_internal(
    news_chunks: List[Dict[str, Any]],
    focus_topic: Optional[str] = None
) -> str:
    """LLM을 사용하여 뉴스 청크들 요약"""
    llm = _get_summarizer_llm()

    if not news_chunks:
        return "관련 뉴스가 없습니다."

    # 뉴스 데이터 포맷팅
    formatted_news = []
    for i, chunk in enumerate(news_chunks[:15], 1):  # 최대 15개
        title = chunk.get("title", "제목 없음")
        document = chunk.get("document", "")[:500]  # 문서 길이 제한
        source = chunk.get("source", "")
        date = chunk.get("published_at", chunk.get("date", ""))

        formatted_news.append(f"""
[뉴스 {i}]
제목: {title}
출처: {source}
날짜: {date}
내용: {document}
""")

    user_prompt = f"""다음 {len(news_chunks)}개의 뉴스 청크를 분석하여 요약하세요:

{"".join(formatted_news)}

{f"[분석 초점]: {focus_topic}" if focus_topic else ""}

[주요 이슈], [시장 영향], [키워드], [타임라인] 형식으로 요약하세요."""

    messages = [
        {"role": "system", "content": NEWS_SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response = llm.invoke(messages)
    return response.content.strip()


@tool
def summarize_news_chunks(
    news_chunks: List[Dict[str, Any]],
    focus_topic: Optional[str] = None
) -> str:
    """
    뉴스 청크들을 분석하여 핵심 내용을 요약합니다.

    Args:
        news_chunks: VectorNewsResult 리스트 (dict 형태)
            - title: 뉴스 제목
            - document: 뉴스 본문/요약
            - source: 출처
            - published_at: 발행일
        focus_topic: 분석 초점 (예: "BTC 급등 원인")

    Returns:
        뉴스 분석 요약 문자열

    Examples:
        summary = summarize_news_chunks(
            news_chunks=[{"title": "BTC ETF 승인", "document": "...", ...}, ...],
            focus_topic="10월 비트코인 이슈"
        )
    """
    try:
        if not news_chunks:
            return "관련 뉴스가 없습니다."

        summary = _summarize_news_internal(news_chunks, focus_topic)
        logger.info(f"News summary generated: {len(summary)} chars from {len(news_chunks)} chunks")
        return summary

    except Exception as e:
        error_msg = f"뉴스 요약 실패: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# ==================== Combined Summary ====================

COMBINED_SUMMARY_SYSTEM_PROMPT = """당신은 암호화폐 종합 분석 전문가입니다.

[역할]
가격 데이터와 뉴스 데이터를 종합하여 인사이트를 도출합니다.

[분석 항목]
1. 가격-뉴스 상관관계: 특정 뉴스가 가격에 미친 영향
2. 인과관계 분석: 급등/급락의 원인 추정
3. 종합 판단: 시장 상황 요약

[출력 형식]
종합 분석 리포트 형태:
- 가격 동향 요약
- 관련 뉴스 요약
- 상관관계 분석
- 결론 및 인사이트
"""


@traceable(name="Summarizer.combined", run_type="llm")
def _summarize_combined_internal(
    coin_name: str,
    price_summary: str,
    news_summary: str,
    user_query: Optional[str] = None
) -> str:
    """가격과 뉴스를 종합한 분석 생성"""
    llm = _get_summarizer_llm()

    user_prompt = f"""다음 {coin_name} 분석 결과를 종합하여 인사이트를 도출하세요:

[가격 분석]
{price_summary}

[뉴스 분석]
{news_summary}

{f"[사용자 질문]: {user_query}" if user_query else ""}

가격-뉴스 상관관계와 종합 인사이트를 제공하세요."""

    messages = [
        {"role": "system", "content": COMBINED_SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response = llm.invoke(messages)
    return response.content.strip()


@tool
def summarize_combined(
    coin_name: str,
    price_summary: str,
    news_summary: str,
    user_query: Optional[str] = None
) -> str:
    """
    가격 데이터 요약과 뉴스 요약을 종합하여 최종 인사이트를 생성합니다.

    Args:
        coin_name: 코인 심볼 (BTC, ETH 등)
        price_summary: summarize_price_data 결과
        news_summary: summarize_news_chunks 결과
        user_query: 원래 사용자 질문 (컨텍스트용)

    Returns:
        종합 분석 리포트 문자열

    Examples:
        report = summarize_combined(
            coin_name="BTC",
            price_summary="BTC 10월 +15% 상승...",
            news_summary="[주요 이슈] ETF 승인...",
            user_query="10월 비트코인 급등 원인"
        )
    """
    try:
        report = _summarize_combined_internal(coin_name, price_summary, news_summary, user_query)
        logger.info(f"Combined summary generated for {coin_name}: {len(report)} chars")
        return report

    except Exception as e:
        error_msg = f"종합 분석 실패 ({coin_name}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg
