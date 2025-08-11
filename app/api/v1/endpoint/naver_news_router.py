"""Naver News API 라우터"""
from fastapi import APIRouter, HTTPException, Query
from app.services.naver_news_api_service import NaverNewsAPIClient
from app.services.naver_news_search_service import NaverNewsSearchService

naver_news_router = APIRouter(prefix="/naver-news", tags=["naver-news"])
# 싱글톤 인스턴스
_naver_client_instance = None
_naver_news_search_service = None

def get_naver_news_client() -> NaverNewsAPIClient:
    """NaverNewsAPIClient 싱글톤 인스턴스 반환"""
    global _naver_client_instance
    if _naver_client_instance is None:
        _naver_client_instance = NaverNewsAPIClient()
    return _naver_client_instance

def get_naver_news_search_service() -> NaverNewsSearchService:
    global _naver_news_search_service
    if _naver_news_search_service is None:
        _naver_news_search_service = NaverNewsSearchService()
    return _naver_news_search_service

@naver_news_router.get("/search", response_model=dict)
def search_news(
    query: str = Query(..., description="검색어"),
    display: int = Query(default=100, ge=1, le=100, description="검색 결과 출력 건수"),
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
        service = get_naver_news_search_service()
        return service.search_news(
            query=query,
            display=display,
            start=start,
            sort=sort
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"뉴스 검색 중 오류 발생: {str(e)}")