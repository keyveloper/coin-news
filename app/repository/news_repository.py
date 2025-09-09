# -*- coding: utf-8 -*-
"""
ChromaDB 뉴스 데이터베이스 Repository

통합 search 메서드로 query string을 받아 내부에서 embedding 처리
"""
import logging
from typing import List, Dict, Optional, Literal
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from app.config.chroma_config import get_chroma_client
from app.schemas.vector_news import VectorNewsResult, VectorNewsBasic

logger = logging.getLogger(__name__)

# Embedding model singleton
_embedding_model = None


def _get_embedding_model():
    """Get or initialize embedding model"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
        logger.info("Embedding model initialized")
    return _embedding_model


class NewsRepository:
    """뉴스 데이터 Repository (Singleton)"""
    _instance: Optional["NewsRepository"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._collection_name = "coin_news"

            self.client = get_chroma_client()
            self.collection = self.client.get_client().get_or_create_collection(
                name=self._collection_name,
            )
            logger.info(f"NewsRepository initialized (collection: {self._collection_name})")

    # ==================== 통합 검색 메서드 ====================

    def search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        pivot_date: Optional[int] = None,
        date_range: Optional[Literal["day", "week", "month"]] = None,
        title_contains: Optional[str] = None,
        source: Optional[str] = None
    ) -> List[VectorNewsResult]:
        """
        통합 시맨틱 뉴스 검색

        Args:
            query: 검색할 쿼리 문자열 (내부에서 embedding 변환)
            top_k: 반환할 최대 결과 개수 (기본값: 10)
            similarity_threshold: 유사도 임계값 0~1 (기본값: 0.7)
            pivot_date: 기준 날짜 (epoch timestamp, 00:00:00)
            date_range: 날짜 범위 ("day": 1일, "week": 7일, "month": 30일)
            title_contains: 제목에 포함될 문자열 (메타데이터 필터)
            source: 뉴스 출처 필터

        Returns:
            List[VectorNewsResult]: 검색된 뉴스 리스트

        Examples:
            # 기본 검색
            search("BTC 가격 상승", top_k=15)

            # 특정 날짜 하루 검색
            search("ETH DeFi", pivot_date=1727740800)

            # 날짜 범위 검색 (pivot_date 기준 7일)
            search("XRP 규제", pivot_date=1727740800, date_range="week")
        """
        try:
            # 1. Query를 embedding으로 변환
            logger.info(f"Search query: {query}")
            model = _get_embedding_model()
            query_embedding = model.embed_query(query)

            # 2. where 조건 빌드
            where_conditions = self._build_where_conditions(
                pivot_date=pivot_date,
                date_range=date_range,
                title_contains=title_contains,
                source=source
            )

            # 3. ChromaDB 검색
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
            }
            if where_conditions:
                query_params["where"] = where_conditions

            results = self.collection.query(**query_params)

            # 4. 결과 포맷팅 및 필터링
            return self._format_results(results, similarity_threshold)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _build_where_conditions(
        self,
        pivot_date: Optional[int],
        date_range: Optional[str],
        title_contains: Optional[str],
        source: Optional[str]
    ) -> Optional[Dict]:
        """where 조건 빌드"""
        conditions = []

        # 날짜 필터
        if pivot_date is not None:
            date_start, date_end = self._calculate_date_range(pivot_date, date_range)
            conditions.append({"publish_date": {"$gte": date_start}})
            conditions.append({"publish_date": {"$lte": date_end}})

        # 출처 필터
        if source:
            conditions.append({"source": source})

        # 조건이 없으면 None
        if not conditions:
            return None

        # 조건이 1개면 그대로, 여러개면 $and
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _calculate_date_range(
        self,
        pivot_date: int,
        date_range: Optional[str]
    ) -> tuple[int, int]:
        """날짜 범위 계산"""
        range_offsets = {
            "day": 86400,        # 1일
            "week": 7 * 86400,   # 7일
            "month": 30 * 86400  # 30일
        }

        if date_range is None:
            # 하루 (pivot_date ~ pivot_date + 23:59:59)
            return pivot_date, pivot_date + 86399
        else:
            offset = range_offsets.get(date_range, 86400)
            return pivot_date - offset, pivot_date + offset

    def _format_results(
        self,
        results: Dict,
        similarity_threshold: float
    ) -> List[VectorNewsResult]:
        """검색 결과 포맷팅"""
        search_results = []

        if not results.get('metadatas') or not results['metadatas'][0]:
            return search_results

        for idx, metadata in enumerate(results['metadatas'][0]):
            distance = results['distances'][0][idx] if results.get('distances') else None
            similarity_score = 1 - distance if distance is not None else None

            # similarity_threshold 필터링
            if similarity_score is not None and similarity_score >= similarity_threshold:
                search_results.append(VectorNewsResult(
                    title=metadata.get('title'),
                    url=metadata.get('url'),
                    link=metadata.get('link'),
                    created_at=metadata.get('created_at'),
                    publish_date=metadata.get('publish_date'),
                    publish_date_readable=metadata.get('publish_date_readable'),
                    source=metadata.get('source'),
                    query=metadata.get('query'),
                    distance=distance,
                    similarity_score=similarity_score,
                    document=results['documents'][0][idx] if results.get('documents') else None
                ))

        return search_results

    # ==================== 기타 메서드 ====================

    def add_news(self, news_items: List[Dict[str, str]]) -> int:
        """뉴스 추가"""
        if not news_items:
            return 0

        documents = []
        metadatas = []
        ids = []

        for idx, item in enumerate(news_items):
            title = item.get('title', '제목 없음')
            url = item.get('url', '')

            documents.append(title)
            metadatas.append({
                'url': url,
                'title': title,
                'created_at': datetime.now().isoformat()
            })
            ids.append(f"news_{hash(url)}_{idx}")

        try:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"Added {len(news_items)} news items")
            return len(news_items)
        except Exception as e:
            logger.error(f"Failed to add news: {e}")
            return 0

    def find_all_news(self, limit: Optional[int] = None) -> List[VectorNewsBasic]:
        """전체 뉴스 조회"""
        try:
            count = self.collection.count()
            if count == 0:
                return []

            results = self.collection.get(limit=limit if limit else count)

            return [
                VectorNewsBasic(
                    title=metadata.get('title'),
                    url=metadata.get('url'),
                    created_at=metadata.get('created_at')
                )
                for metadata in results.get('metadatas', [])
            ]
        except Exception as e:
            logger.error(f"Failed to get news: {e}")
            return []

    def delete_news_by_url(self, url: str) -> bool:
        """URL로 뉴스 삭제"""
        try:
            self.collection.delete(where={"url": url})
            logger.info(f"Deleted news: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete news: {e}")
            return False

    def count(self) -> int:
        return self.collection.count()

    def get_stats(self) -> Dict:
        return {
            'total_count': self.count(),
            'collection_name': self.collection.name
        }
