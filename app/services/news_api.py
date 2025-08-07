"""News API 연동 모듈"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime


class NewsAPIClient:
    """News API에서 뉴스 데이터를 가져오는 클라이언트"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2"

    def get_top_headlines(self, query: str = "cryptocurrency", page_size: int = 10) -> List[Dict]:
        """최신 헤드라인 뉴스 가져오기"""
        url = f"{self.base_url}/top-headlines"
        params = {
            "apiKey": self.api_key,
            "q": query,
            "pageSize": page_size,
            "language": "en"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        return self._format_articles(data.get("articles", []))

    def get_everything(self, query: str = "bitcoin", page_size: int = 10) -> List[Dict]:
        """모든 뉴스 검색"""
        url = f"{self.base_url}/everything"
        params = {
            "apiKey": self.api_key,
            "q": query,
            "pageSize": page_size,
            "sortBy": "publishedAt"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        return self._format_articles(data.get("articles", []))

    def _format_articles(self, articles: List[Dict]) -> List[Dict]:
        """뉴스 데이터 포맷 정리 (MongoDB 저장용)"""
        formatted = []
        for article in articles:
            url = article.get("url", "")
            if not url:
                continue

            formatted.append({
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "url": url,
                "source": article.get("source", {}).get("name", ""),
                "published_at": article.get("publishedAt", ""),
                "content": article.get("content", ""),
                "author": article.get("author", ""),
                "image_url": article.get("urlToImage", ""),
                "fetched_at": datetime.utcnow().isoformat()
            })
        return formatted