"""Naver News API 라우터"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.naver_news_api_service import NaverNewsAPIClient
from app.schemas.naver_news import NaverNewsAPIResponse

naver_news_router = APIRouter(prefix="/naver-news", tags=["naver-news"])

# 싱글톤 인스턴스
_naver_client_instance = None


def get_naver_news_client() -> NaverNewsAPIClient:
    """NaverNewsAPIClient 싱글톤 인스턴스 반환"""
    global _naver_client_instance
    if _naver_client_instance is None:
        _naver_client_instance = NaverNewsAPIClient()
    return _naver_client_instance


@naver_news_router.get("/bitcoin", response_model=dict)
def get_bitcoin_news(
    display: int = Query(default=10, ge=1, le=100, description="검색 결과 출력 건수"),
    start: int = Query(default=1, ge=1, description="검색 시작 위치"),
    sort: str = Query(default="date", pattern="^(sim|date)$", description="정렬 옵션")
):
    """
    비트코인 관련 뉴스 검색

    Args:
        display: 검색 결과 출력 건수 (1~100)
        start: 검색 시작 위치
        sort: 정렬 옵션 (sim: 정확도순, date: 날짜순)

    Returns:
        JSON 형태의 뉴스 데이터
    """
    try:
        client = get_naver_news_client()
        response = client.search_news(
            query="비트코인",
            display=display,
            start=start,
            sort=sort
        )

        return {
            "status": "success",
            "message": f"비트코인 관련 뉴스 {len(response.items)}건을 가져왔습니다.",
            "data": {
                "lastBuildDate": response.lastBuildDate,
                "total": response.total,
                "start": response.start,
                "display": response.display,
                "items": [item.model_dump() for item in response.items]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"뉴스 검색 중 오류 발생: {str(e)}")


@naver_news_router.get("/search", response_model=dict)
def search_news(
    query: str = Query(..., description="검색어"),
    display: int = Query(default=10, ge=1, le=100, description="검색 결과 출력 건수"),
    start: int = Query(default=1, ge=1, description="검색 시작 위치"),
    sort: str = Query(default="date", pattern="^(sim|date)$", description="정렬 옵션")
):
    """
    사용자 지정 키워드로 뉴스 검색

    Args:
        query: 검색어
        display: 검색 결과 출력 건수 (1~100)
        start: 검색 시작 위치
        sort: 정렬 옵션 (sim: 정확도순, date: 날짜순)

    Returns:
        JSON 형태의 뉴스 데이터
    """
    try:
        client = get_naver_news_client()
        response = client.search_news(
            query=query,
            display=display,
            start=start,
            sort=sort
        )

        return {
            "status": "success",
            "message": f"'{query}' 관련 뉴스 {len(response.items)}건을 가져왔습니다.",
            "data": {
                "lastBuildDate": response.lastBuildDate,
                "total": response.total,
                "start": response.start,
                "display": response.display,
                "items": [item.model_dump() for item in response.items]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"뉴스 검색 중 오류 발생: {str(e)}")


@naver_news_router.get("/bitcoin/mongodb", response_model=dict)
def get_bitcoin_news_for_mongodb(
    display: int = Query(default=10, ge=1, le=100, description="검색 결과 출력 건수"),
    sort: str = Query(default="date", pattern="^(sim|date)$", description="정렬 옵션")
):
    """
    비트코인 관련 뉴스를 MongoDB 저장용 포맷으로 반환

    Args:
        display: 검색 결과 출력 건수 (1~100)
        sort: 정렬 옵션 (sim: 정확도순, date: 날짜순)

    Returns:
        MongoDB 저장용 JSON 데이터
    """
    try:
        client = get_naver_news_client()
        formatted_news = client.get_news_for_mongodb(
            query="비트코인",
            display=display,
            sort=sort
        )

        return {
            "status": "success",
            "message": f"비트코인 관련 뉴스 {len(formatted_news)}건을 가져왔습니다 (MongoDB 저장용 포맷).",
            "data": {
                "total_items": len(formatted_news),
                "items": formatted_news
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"뉴스 검색 중 오류 발생: {str(e)}")