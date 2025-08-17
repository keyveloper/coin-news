"""Naver News API 라우터"""
from fastapi import APIRouter, HTTPException, Query
from app.services.naver_news_api_service import NaverNewsAPIClient

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

