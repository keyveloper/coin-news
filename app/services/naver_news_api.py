"""Naver News API 연동 모듈"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime
import re
from urllib.parse import quote
from app.schemas.naver_news import (
    NaverNewsRequest,
    NaverNewsAPIResponse,
    NaverNewsItem
)


class NaverNewsAPIClient:
    """Naver News API에서 뉴스 데이터를 가져오는 클라이언트"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID", "USER_SECRET")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET", "USER_SECRET")
        self.base_url = "https://openapi.naver.com/v1/search/news.json"

    def search_news(
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

    def get_news_for_mongodb(
        self,
        query: str,
        display: int = 10,
        sort: str = "date"
    ) -> List[Dict]:
        """MongoDB 저장용 뉴스 데이터 가져오기

        Args:
            query: 검색어
            display: 검색 결과 출력 건수
            sort: 정렬 옵션

        Returns:
            List[Dict]: MongoDB 저장용 뉴스 데이터 리스트
        """
        api_response = self.search_news(query=query, display=display, sort=sort)
        return self._format_for_mongodb(api_response.items, query)

    def _format_for_mongodb(
        self,
        items: List[NaverNewsItem],
        query: str
    ) -> List[Dict]:
        """Naver 뉴스 데이터를 MongoDB 저장용 포맷으로 변환"""
        formatted = []

        for item in items:
            # HTML 태그 제거
            clean_title = self._remove_html_tags(item.title)
            clean_description = self._remove_html_tags(item.description)

            formatted.append({
                "title": clean_title,
                "description": clean_description,
                "url": item.originallink,
                "naver_link": item.link,
                "source": "Naver News",
                "published_at": item.pubDate,
                "search_query": query,
                "fetched_at": datetime.utcnow().isoformat()
            })

        return formatted

    @staticmethod
    def _remove_html_tags(text: str) -> str:
        """HTML 태그 제거 (<b>, </b> 등)"""
        clean = re.sub(r'<[^>]+>', '', text)
        return clean.strip()