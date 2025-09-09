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

PRICE_SUMMARY_SYSTEM_PROMPT = """암호화폐 가격 분석가. 3-5문장으로 요약.
분석: 추세, 변동폭, 변곡점, 핵심 수치 포함."""


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

    # 가격 데이터를 {날짜: 종가} map으로 변환 (전체 데이터)
    price_map = {
        p.get("date", "unknown"): p.get("close", p.get("price", 0))
        for p in price_data
        if p.get("date")
    }

    user_prompt = f"""다음 {coin_name} 가격 데이터를 분석하여 요약하세요:

[통계 요약]
- 기간: {len(price_data)}개 데이터 포인트
- 시작가: ${first:,.2f}
- 종가: ${last:,.2f}
- 최고가: ${high:,.2f}
- 최저가: ${low:,.2f}
- 변동률: {change_pct:+.2f}%

[일별 종가 데이터]
{price_map}

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

NEWS_SUMMARY_SYSTEM_PROMPT = """암호화폐 뉴스 분석가. 5-10문장으로 요약.
형식: [주요 이슈] [시장 영향] [키워드] [타임라인]"""


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
