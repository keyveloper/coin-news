from langchain_community.document_loaders import WebBaseLoader
from typing import Optional, List, Dict
from langchain_core.documents import Document
from app.services.naver_news_api_service import NaverNewsAPIClient


class NaverNewsSearchService:
    """네이버 뉴스 검색 서비스 (Singleton)"""

    _instance: Optional['NaverNewsSearchService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Singleton 패턴에서 중복 초기화 방지
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._api_client = NaverNewsAPIClient()

    def __extract_news_metadata_from_url(self, urls: List[str]) -> List[Document]:
        loader = WebBaseLoader(web_paths=urls)
        docs = loader.load()
        return docs

    def __preprocess_page_content(self, content: str) -> str:
        """
        페이지 콘텐츠 전처리

        Args:
            content: 원본 텍스트

        Returns:
            전처리된 텍스트 (줄바꿈 제거, 연속 공백 제거)
        """
        import re
        # \n 제거
        content = content.replace('\n', ' ')
        # 연속된 공백을 하나로 치환
        content = re.sub(r'\s+', ' ', content)
        # 양쪽 공백 제거
        content = content.strip()
        return content

    def search_news(
        self,
        query: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date"
    ) -> Dict:
        # response = NaverNewsResponse
        response = self._api_client.fetch_news(
            query=query,
            display=display,
            start=start,
            sort=sort
        )

        originallinks = [item.originallink for item in response.items]
        docs = self.__extract_news_metadata_from_url(originallinks)

        # 각 문서의 page_content 전처리 및 URL별 매핑
        docs_by_url = {}
        for doc in docs:
            doc.page_content = self.__preprocess_page_content(doc.page_content)
            # metadata에서 source URL 추출
            url = doc.metadata.get('source', '')
            docs_by_url[url] = doc

        # 각 item에 해당하는 doc 추가
        items_with_docs = []
        for item in response.items:
            item_dict = item.model_dump()
            doc = docs_by_url.get(item.originallink)

            if doc:
                item_dict['document'] = {
                    'metadata': doc.metadata,
                    'page_content': doc.page_content
                }
            else:
                item_dict['document'] = None

            items_with_docs.append(item_dict)

        return {
            "status": "success",
            "message": f"'{query}' 관련 뉴스 {len(response.items)}건을 가져왔습니다.",
            "data": {
                "lastBuildDate": response.lastBuildDate,
                "total": response.total,
                "start": response.start,
                "display": response.display,
                "items": items_with_docs
            }
        }