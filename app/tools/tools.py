from typing import Dict, List
from langchain.tools import tool
from app.agent.query_analyzer_agent import QueryAnalyzerService
from app.repository.news_repository import NewsRepository
from app.repository.price_repository import PriceRepository


@tool
def search_news_by_semantic_query(
    query_embedding: List[float],
    top_k: int = 10,
    similarity_threshold: float = 0.7
) -> List[Dict]:
    """
    임베딩 벡터로 의미적으로 유사한 뉴스를 검색합니다.

    Args:
        query_embedding: 쿼리의 임베딩 벡터
        top_k: 반환할 최대 결과 개수 (기본값: 10)
        similarity_threshold: 유사도 임계값 0~1 (기본값: 0.7)

    Returns:
        검색된 뉴스 리스트
    """
    repo = NewsRepository()
    return repo.find_news_by_semantic_query(query_embedding, top_k, similarity_threshold)


@tool
def search_news_by_semantic_query_with_date(
    query_embedding: List[float],
    pivot_date: int,
    top_k: int = 10,
    similarity_threshold: float = 0.7
) -> List[Dict]:
    """
    특정 날짜(하루) 범위 내에서 임베딩 벡터로 뉴스를 검색합니다.

    Args:
        query_embedding: 쿼리의 임베딩 벡터
        pivot_date: 기준 날짜 (epoch time, 00:00:00이어야 함)
        top_k: 반환할 최대 결과 개수
        similarity_threshold: 유사도 임계값 0~1

    Returns:
        검색된 뉴스 리스트 (해당 날짜 하루 동안)
    """
    repo = NewsRepository()
    return repo.find_by_semantic_query_with_one_day_range(
        query_embedding, top_k, similarity_threshold, pivot_date
    )

# ==================== PriceRepository Tools ====================
# plannings: [ "tool": "get_price_by_hour_range", "parameters": "coin_news: " ]
@tool
def get_price_by_hour_range(coin_name: str, spot_time: int) -> List[Dict]:
    """
    기준 시간으로부터 1시간 전/후 가격 데이터를 조회합니다 (각 시간별 high, low).

    Args:
        coin_name: 코인 이름 (예: "BTC", "ETH")
        spot_time: 기준 시간 (epoch time)

    Returns:
        시간별 가격 데이터 리스트 [{time, high, low, open, close}]
    """
    repo = PriceRepository()
    return repo.find_by_coin_name_with_hour_range(coin_name, spot_time)


@tool
def get_price_by_oneday(coin_name: str, pivot_date: int) -> List[Dict]:
    """
    기준 날짜의 00:00:00 ~ 23:59:59 가격 데이터를 조회합니다 (마지막 시간대 close 값).

    Args:
        coin_name: 코인 이름
        pivot_date: 기준 날짜 (epoch time, 00:00:00이어야 함)

    Returns:
        날짜별 가격 데이터 [{date, close, time}]
    """
    repo = PriceRepository()
    return repo.find_by_coin_name_with_oneday(coin_name, pivot_date)


@tool
def get_price_week_before(coin_name: str, spot_date: int) -> List[Dict]:
    """
    기준 날짜로부터 1주일 전 가격 데이터를 조회합니다 (각 날짜의 마지막 시간대 close 값).

    Args:
        coin_name: 코인 이름
        spot_date: 기준 시간 (epoch time)

    Returns:
        날짜별 가격 데이터 리스트
    """
    repo = PriceRepository()
    return repo.find_by_coin_name_with_week_before(coin_name, spot_date)


@tool
def get_price_week_after(coin_name: str, spot_date: int) -> List[Dict]:
    """
    기준 날짜로부터 1주일 후 가격 데이터를 조회합니다 (각 날짜의 마지막 시간대 close 값).

    Args:
        coin_name: 코인 이름
        spot_date: 기준 시간 (epoch time)

    Returns:
        날짜별 가격 데이터 리스트
    """
    repo = PriceRepository()
    return repo.find_by_coin_name_with_week_after(coin_name, spot_date)


@tool
def get_price_month_before(coin_name: str, spot_date: int) -> List[Dict]:
    """
    기준 날짜로부터 1개월 전 가격 데이터를 조회합니다 (각 날짜의 마지막 시간대 close 값).

    Args:
        coin_name: 코인 이름
        spot_date: 기준 시간 (epoch time)

    Returns:
        날짜별 가격 데이터 리스트
    """
    repo = PriceRepository()
    return repo.find_by_coin_name_with_month_before(coin_name, spot_date)


@tool
def get_price_month_after(coin_name: str, spot_date: int) -> List[Dict]:
    """
    기준 날짜로부터 1개월 후 가격 데이터를 조회합니다 (각 날짜의 마지막 시간대 close 값).

    Args:
        coin_name: 코인 이름
        spot_date: 기준 시간 (epoch time)

    Returns:
        날짜별 가격 데이터 리스트
    """
    repo = PriceRepository()
    return repo.find_by_coin_name_with_month_after(coin_name, spot_date)


@tool
def get_price_year(coin_name: str, spot_date: int) -> List[Dict]:
    """
    기준 날짜로부터 1년 전 가격 데이터를 조회합니다 (각 날짜의 마지막 시간대 close 값).

    Args:
        coin_name: 코인 이름
        spot_date: 기준 시간 (epoch time)

    Returns:
        날짜별 가격 데이터 리스트
    """
    repo = PriceRepository()
    return repo.find_by_coin_name_with_year(coin_name, spot_date)


@tool
def get_all_price_by_coin(coin_name: str, limit: int = None) -> List[Dict]:
    """
    해당 코인의 모든 가격 데이터를 조회합니다 (각 날짜의 마지막 시간대 close 값).

    Args:
        coin_name: 코인 이름
        limit: 조회 개수 제한 (None이면 전체 조회)

    Returns:
        날짜별 가격 데이터 리스트
    """
    repo = PriceRepository()
    return repo.find_by_coin(coin_name, limit)
