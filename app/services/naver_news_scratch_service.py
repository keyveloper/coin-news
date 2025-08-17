"""네이버 뉴스 스크래치 서비스 - NewsURLLoader를 Singleton으로 관리"""
from typing import Optional, Dict
from langchain_community.document_loaders import NewsURLLoader
from app.services.naver_news_api_service import NaverNewsAPIClient
from app.repository.naver_news_repository import NaverNewsRepository
from app.config.mongodb_config import get_mongodb_client
from app.parser.coinreaders_parser import parse_coinreaders_news
import logging

logger = logging.getLogger(__name__)


class NaverNewsScratchService:
    """
    네이버 뉴스 스크래치 서비스 (Singleton with Dependency Injection)
    NewsURLLoader를 Singleton으로 관리
    """

    _instance: Optional['NaverNewsScratchService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        naver_news_api_client: Optional[NaverNewsAPIClient] = None,
        news_url_loader: Optional[NewsURLLoader] = None,
        repository: Optional[NaverNewsRepository] = None
    ):
        # Singleton 패턴에서 중복 초기화 방지
        if not hasattr(self, '_initialized'):
            self._initialized = True

            # 의존성 주입 (없으면 기본 인스턴스 생성)
            self._naver_news_api_client = naver_news_api_client or NaverNewsAPIClient()

            # NewsURLLoader를 Singleton으로 관리
            self._news_url_loader = news_url_loader or NewsURLLoader(urls=[])

            # Repository 초기화
            if repository:
                self._repository = repository
            else:
                mongodb_client = get_mongodb_client()
                db = mongodb_client.get_database()
                self._repository = NaverNewsRepository(db)

            logger.info(
                f"NaverNewsScratchService 초기화 완료 "
                f"(NewsURLLoader Singleton ID: {id(self._news_url_loader)})"
            )

    def scratch_adn_save_to_mongodb(self, query: str) -> Dict:
        naver_news_api_responses = self._naver_news_api_client.fetch_news(query)
        response_items = naver_news_api_responses.items
        original_links = [item.originallink for item in response_items]

        coinreader_links = []
        filtered_links = []
        for link in original_links:
            if "coinreader" in link:
                coinreader_links.append(link)
            else:
                filtered_links.append(link)

        self._news_url_loader.urls = filtered_links

        try:
            general_docs = self._news_url_loader.load()
            coinreader_docs = [parse_coinreaders_news(url=link) for link in coinreader_links]
        except Exception as e:
            logger.exception("NewsURLLoader.load() 실패")
            return {"query": query, "error": str(e), "count": 0, "saved_documents": []}

        # MongoDB에 저장
        mongodb_client = get_mongodb_client()
        local_db = mongodb_client.get_database("local")
        news_log_collection = local_db.get_collection("news.log")

        saved = []
        saved_count = 0
        failed_count = 0

        # general_docs 저장
        for doc in general_docs:
            try:
                doc_dict = doc.__dict__
                news_log_collection.insert_one(doc_dict)
                saved.append(doc_dict)
                saved_count += 1
            except Exception as e:
                logger.error(f"Document 저장 실패: {e}")
                failed_count += 1

        # coinreader_docs 저장
        for doc in coinreader_docs:
            try:
                doc_dict = doc.model_dump() if hasattr(doc, 'model_dump') else doc.dict()
                news_log_collection.insert_one(doc_dict)
                saved.append(doc_dict)
                saved_count += 1
            except Exception as e:
                logger.error(f"CoinReader Document 저장 실패: {e}")
                failed_count += 1

        logger.info(f"MongoDB 저장 완료 - 성공: {saved_count}, 실패: {failed_count}")

        return {
            "query": query,
            "saved_count": saved_count,
            "failed_count": failed_count,
            "docs": saved
        }




