"""Database Tools for News and Price Repository Access"""
from typing import List, Union, Literal
from langchain.tools import tool
from app.repository.price_repository import PriceRepository
from app.schemas.price import PriceData, PriceHourlyData

# ==================== Price Repository Tool ====================

@tool
def get_coin_price(
    coin_name: str,
    pivot_date: int,
    range_type: Literal["hour", "day", "week", "month", "year"] = "week",
    direction: Literal["before", "after", "both"] = "before"
) -> Union[List[PriceData], List[PriceHourlyData]]:
    """
    코인 가격 데이터를 통합 조회합니다.

    Args:
        coin_name: 코인 심볼 (BTC, ETH, XRP 등)
        pivot_date: 기준 날짜 (epoch timestamp, 00:00:00 권장)
        range_type: 조회 범위 단위
            - "hour": ±1시간 (시간별 OHLC 데이터 반환)
            - "day": 1일
            - "week": 7일 (기본값)
            - "month": 30일
            - "year": 365일
        direction: 기준일 대비 방향
            - "before": 과거 데이터 (기본값) - pivot_date 이전
            - "after": 미래 데이터 - pivot_date 이후
            - "both": 양방향 데이터 - pivot_date 전후

    Returns:
        - range_type="hour": List[PriceHourlyData] - {time, high, low, open, close}
        - 그 외: List[PriceData] - {date, close, time}

    Examples:
        # BTC 7일 전 가격 (기본)
        get_coin_price("BTC", 1727740800)

        # ETH 1개월 후 가격
        get_coin_price("ETH", 1727740800, "month", "after")

        # XRP ±7일 양방향 가격
        get_coin_price("XRP", 1727740800, "week", "both")

        # BTC 시간별 상세 가격
        get_coin_price("BTC", 1727740800, "hour", "both")
    """
    repo = PriceRepository()
    return repo.find_by_range(coin_name, pivot_date, range_type, direction)