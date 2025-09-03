"""
ChromaDB 데이터베이스 작업 유틸리티
"""
from typing import List, Dict, Optional
from datetime import datetime
from app.config.chroma_config import get_chroma_client


class NewsRepository:
    _instance: Optional["NewsRepository"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._collection_name = "coin_news"

            # 내부 필드 변수 생성
            self.client = get_chroma_client()
            self.collection = self.client.get_client().get_or_create_collection(
                name=self._collection_name,
            )

    def add_news(self, news_items: List[Dict[str, str]]) -> int:
        if not news_items:
            print("추가할 뉴스가 없습니다.")
            return 0

        # 데이터 준비
        documents = []
        metadatas = []
        ids = []

        for idx, item in enumerate(news_items):
            title = item.get('title', '제목 없음')
            url = item.get('url', '')

            # 문서 텍스트 (임베딩할 내용)
            documents.append(title)

            # 메타데이터
            metadatas.append({
                'url': url,
                'title': title,
                'created_at': datetime.now().isoformat()
            })

            # 고유 ID (URL 기반 해시 또는 타임스탬프)
            doc_id = f"news_{hash(url)}_{idx}"
            ids.append(doc_id)

        # ChromaDB에 추가
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✅ {len(news_items)}개 뉴스 추가 완료")
            return len(news_items)
        except Exception as e:
            print(f"❌ 뉴스 추가 실패: {e}")
            return 0

    def find_news_by_semantic_query(
        self,
        query_embedding: List[float],
        tok_k: int,
        similarity_threshold: float,
    ) -> List[Dict]:
        try:
            # ChromaDB의 query 메서드로 벡터 검색
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=tok_k,
            )

            # 결과 포맷팅 및 필터링
            search_results = []
            if results['metadatas'] and results['metadatas'][0]:
                for idx, metadata in enumerate(results['metadatas'][0]):
                    distance = results['distances'][0][idx] if results.get('distances') else None

                    # similarity score 계산 (1 - distance)
                    similarity_score = 1 - distance if distance is not None else None

                    # similarity_threshold 필터링
                    if similarity_score is not None and similarity_score >= similarity_threshold:
                        search_results.append({
                            'title': metadata.get('title'),
                            'url': metadata.get('url'),
                            'created_at': metadata.get('created_at'),
                            'distance': distance,
                            'similarity_score': similarity_score,
                            'document': results['documents'][0][idx] if results.get('documents') else None
                        })

            return search_results
        except Exception as e:
            print(f"❌ 임베딩 검색 실패: {e}")
            return []

    def find_by_semantic_query_with_one_day_range(
        self,
        query_embedding: List[float],
        tok_k: int,
        similarity_threshold: float,
        pivot_date: int
    ) -> List[Dict]:
        try:
            # pivot_date가 00:00:00인지 확인
            pivot_dt = datetime.fromtimestamp(pivot_date)
            if pivot_dt.hour != 0 or pivot_dt.minute != 0 or pivot_dt.second != 0:
                raise ValueError(
                    f"pivot_date는 00:00:00이어야 합니다. "
                    f"현재: {pivot_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            # date_end 계산: pivot_date의 23:59:59
            date_start = pivot_date
            date_end = pivot_date + (24 * 60 * 60 - 1)  # +86399초 (23시간 59분 59초)

            # ChromaDB의 query 메서드로 벡터 검색
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=tok_k,
                where={
                    "$and": [
                        {"publish_date": {"$gte": date_start}},
                        {"publish_date": {"$lte": date_end}},
                    ]
                }
            )

            # 결과 포맷팅 및 필터링
            search_results = []
            if results['metadatas'] and results['metadatas'][0]:
                for idx, metadata in enumerate(results['metadatas'][0]):
                    distance = results['distances'][0][idx] if results.get('distances') else None

                    # similarity score 계산 (1 - distance)
                    similarity_score = 1 - distance if distance is not None else None

                    # similarity_threshold 필터링
                    if similarity_score is not None and similarity_score >= similarity_threshold:
                        search_results.append({
                            'title': metadata.get('title'),
                            'link': metadata.get('link'),
                            'publish_date': metadata.get('publish_date'),
                            'publish_date_readable': metadata.get('publish_date_readable'),
                            'source': metadata.get('source'),
                            'query': metadata.get('query'),
                            'distance': distance,
                            'similarity_score': similarity_score,
                            'document': results['documents'][0][idx] if results.get('documents') else None
                        })

            return search_results
        except ValueError as ve:
            print(f"❌ 날짜 검증 실패: {ve}")
            raise  # ValueError는 다시 던져서 Service에서 처리
        except Exception as e:
            print(f"❌ 임베딩 검색 실패: {e}")
            return []

    def find_all_news(self, limit: Optional[int] = None) -> List[Dict]:
        try:
            count = self.collection.count()
            if count == 0:
                return []

            results = self.collection.get(
                limit=limit if limit else count
            )

            news_list = []
            if results['metadatas']:
                for metadata in results['metadatas']:
                    news_list.append({
                        'title': metadata.get('title'),
                        'url': metadata.get('url'),
                        'created_at': metadata.get('created_at')
                    })

            return news_list
        except Exception as e:
            print(f"❌ 뉴스 조회 실패: {e}")
            return []

    def delete_news_by_url(self, url: str) -> bool:
        try:
            # URL로 필터링하여 삭제
            self.collection.delete(
                where={"url": url}
            )
            print(f"✅ 뉴스 삭제 완료: {url}")
            return True
        except Exception as e:
            print(f"❌ 뉴스 삭제 실패: {e}")
            return False

    def count(self) -> int:
        return self.collection.count()

    def get_stats(self) -> Dict:
        return {
            'total_count': self.count(),
            'collection_name': self.collection.name
        }