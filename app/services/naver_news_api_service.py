"""Naver News API 연동 모듈"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime
import re
import logging
from urllib.parse import quote
from app.schemas.naver_news import (
    NaverNewsRequest,
    NaverNewsAPIResponse,
    NaverNewsItem
)

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NaverNewsAPIClient:
    """Naver News API에서 뉴스 데이터를 가져오는 클라이언트"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        self.client_id = client_id or os.getenv("X-Naver-Client-Id")
        self.client_secret = client_secret or os.getenv("X-Naver-Client-Secret")
        self.base_url = "https://openapi.naver.com/v1/search/news.json"


    def fetch_news(
        self,
        query: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date"
    ) -> NaverNewsAPIResponse:
        """뉴스 검색

        Args:
            query: 검색어
            display: 검색 결과 출력 건수 (1~100)
            start: 검색 시작 위치 (1~1000)
            sort: 정렬 옵션 (sim: 정확도순, date: 날짜순)

        Returns:
            NaverNewsAPIResponse: API 응답 객체
        """
        # 요청 파라미터 검증
        request_params = NaverNewsRequest(
            query=query,
            display=display,
            start=start,
            sort=sort
        )

        # HTTP 헤더 설정
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "User-Agent": "Mozilla/5.0"
        }

        # 검색어 UTF-8 URL 인코딩 (safe='' 로 모든 특수문자 인코딩)
        encoded_query = quote(request_params.query, safe='')

        # API 요청 (query는 인코딩된 값을 직접 URL에 포함)
        url_with_params = (
            f"{self.base_url}?"
            f"query={encoded_query}&"
            f"display={request_params.display}&"
            f"start={request_params.start}&"
            f"sort={request_params.sort}"
        )

        response = requests.get(
            url_with_params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        # JSON 응답 파싱
        data = response.json()
        return NaverNewsAPIResponse(**data)

    def fetch_news_by_date(
        self,
        query: str,
        start_date: str,
        end_date: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date"
    ) -> NaverNewsAPIResponse:
        """날짜 범위로 뉴스 검색

        Args:
            query: 검색어
            start_date: 시작 날짜 (YYYYMMDD 형식, 예: 20240101)
            end_date: 종료 날짜 (YYYYMMDD 형식, 예: 20240131)
            display: 검색 결과 출력 건수 (1~100)
            start: 검색 시작 위치 (1~1000)
            sort: 정렬 옵션 (sim: 정확도순, date: 날짜순)

        Returns:
            NaverNewsAPIResponse: API 응답 객체
        """
        # 날짜 범위를 쿼리에 추가
        # 네이버 검색 API는 날짜 필터를 지원하지 않으므로 검색어에 날짜를 포함
        date_query = f"{query} {start_date}..{end_date}"

        logger.info(f"날짜 범위 검색: {date_query}")

        return self.fetch_news(
            query=date_query,
            display=display,
            start=start,
            sort=sort
        )
