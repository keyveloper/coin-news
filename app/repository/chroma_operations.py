"""
ChromaDB 데이터베이스 작업 유틸리티
"""
from typing import List, Dict, Optional
from datetime import datetime
from app.config.chroma_config import get_chroma_client, COLLECTION_NAME


class ChromaNewsDB:
    """코인 뉴스 ChromaDB 작업 클래스"""

    def __init__(self, collection_name: str = COLLECTION_NAME):
        """
        Args:
            collection_name: 사용할 컬렉션 이름
        """
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(collection_name)

    def add_news(self, news_items: List[Dict[str, str]]) -> int:
        """
        뉴스 데이터를 ChromaDB에 추가
        Args:
            news_items: [{'title': str, 'url': str}, ...] 형식의 뉴스 리스트
        Returns:
            추가된 뉴스 개수
        """
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

    def search_news(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        제목 기반 유사 뉴스 검색
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 개수
        Returns:
            검색 결과 리스트
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )

            # 결과 포맷팅
            search_results = []
            if results['metadatas'] and results['metadatas'][0]:
                for idx, metadata in enumerate(results['metadatas'][0]):
                    search_results.append({
                        'title': metadata.get('title'),
                        'url': metadata.get('url'),
                        'created_at': metadata.get('created_at'),
                        'distance': results['distances'][0][idx] if results.get('distances') else None
                    })

            return search_results
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []

    def get_all_news(self, limit: Optional[int] = None) -> List[Dict]:
        """
        모든 뉴스 가져오기
        Args:
            limit: 최대 개수 제한 (None이면 전체)
        Returns:
            뉴스 리스트
        """
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
        """
        URL로 뉴스 삭제
        Args:
            url: 삭제할 뉴스 URL
        Returns:
            삭제 성공 여부
        """
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

    def clear_all(self) -> bool:
        """
        모든 뉴스 삭제
        Returns:
            삭제 성공 여부
        """
        try:
            # 컬렉션 리셋
            self.client.reset_collection(self.collection.name)
            self.collection = self.client.get_or_create_collection(self.collection.name)
            print("✅ 모든 뉴스 삭제 완료")
            return True
        except Exception as e:
            print(f"❌ 뉴스 삭제 실패: {e}")
            return False

    def count(self) -> int:
        """
        저장된 뉴스 개수 반환
        """
        return self.collection.count()

    def get_stats(self) -> Dict:
        """
        데이터베이스 통계 정보
        """
        return {
            'total_count': self.count(),
            'collection_name': self.collection.name
        }