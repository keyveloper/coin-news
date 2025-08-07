"""뉴스 데이터 저장/조회 레포지토리"""
from typing import List, Dict, Optional
from datetime import datetime
from app.db.mongodb_client import MongoDBClient


class NewsRepository:
    """뉴스 데이터를 MongoDB에 저장하고 조회하는 레포지토리"""

    def __init__(self, mongodb_client: MongoDBClient):
        self.db = mongodb_client
        self.collection = self.db.get_collection("news_articles")

    def save_article(self, article: Dict) -> bool:
        """단일 뉴스 기사 저장"""
        try:
            article["_id"] = self._generate_id(article)
            article["created_at"] = datetime.utcnow()

            self.collection.insert_one(article)
            return True
        except Exception:
            return False

    def save_articles(self, articles: List[Dict]) -> int:
        """여러 뉴스 기사 일괄 저장"""
        saved_count = 0
        for article in articles:
            if not self.article_exists(article):
                if self.save_article(article):
                    saved_count += 1
        return saved_count

    def get_article(self, article_id: str) -> Optional[Dict]:
        """뉴스 기사 조회"""
        try:
            result = self.collection.find_one({"_id": article_id})
            if result:
                result.pop("_id", None)
            return result
        except Exception:
            return None

    def get_all_articles(self) -> List[Dict]:
        """모든 뉴스 기사 조회"""
        try:
            results = self.collection.find()
            articles = []
            for doc in results:
                doc.pop("_id", None)
                articles.append(doc)
            return articles
        except Exception:
            return []

    def delete_article(self, article_id: str) -> bool:
        """뉴스 기사 삭제"""
        try:
            result = self.collection.delete_one({"_id": article_id})
            return result.deleted_count > 0
        except Exception:
            return False

    def article_exists(self, article: Dict) -> bool:
        """뉴스 기사 중복 확인"""
        article_id = self._generate_id(article)
        try:
            return self.collection.count_documents({"_id": article_id}) > 0
        except Exception:
            return False

    def _generate_id(self, article: Dict) -> str:
        """뉴스 기사 ID 생성 (URL 기반)"""
        url = article.get("url", "")
        if url:
            return url

        title = article.get("title", "")
        timestamp = article.get("published_at", datetime.utcnow().isoformat())
        return f"{title}:{timestamp}"