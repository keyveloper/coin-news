"""Naver 뉴스 데이터 저장/조회 레포지토리 (Repository Layer)"""
from typing import List, Dict, Optional
from datetime import datetime
from pymongo.errors import DuplicateKeyError
import logging

logger = logging.getLogger(__name__)


class NaverNewsRepository:
    """
    Naver 뉴스 데이터를 MongoDB에 저장하고 조회하는 레포지토리
    Data Access Layer - MongoDB 직접 접근
    """

    def __init__(self, db):
        """
        NaverNewsRepository 초기화

        Args:
            db: MongoDB Database 객체
        """
        self.db = db
        self._create_indexes()

    def _create_indexes(self):
        """MongoDB 컬렉션 인덱스 생성"""
        try:
            # news.log 컬렉션에 인덱스 생성
            news_log_collection = self.db.get_collection("news.log")
            news_log_collection.create_index("url", unique=True)
            news_log_collection.create_index("saved_at")
            news_log_collection.create_index("search_query")
            news_log_collection.create_index("published_date")

            # news.raw 컬렉션에 인덱스 생성
            news_raw_collection = self.db.get_collection("news.raw")
            news_raw_collection.create_index("url", unique=True)
            news_raw_collection.create_index("fetched_at")
            news_raw_collection.create_index("query")

            logger.info("MongoDB 인덱스 생성 완료")
        except Exception as e:
            logger.warning(f"인덱스 생성 중 경고: {e}")

    # ==================== news.log 컬렉션 (파싱된 메타데이터) ====================

    def save_news_metadata(self, metadata: Dict) -> bool:
        """
        파싱된 뉴스 메타데이터를 news.log 컬렉션에 저장
        db.getCollection("news.log").insertOne() 메서드 사용

        Args:
            metadata: 저장할 메타데이터

        Returns:
            bool: 저장 성공 여부

        Raises:
            DuplicateKeyError: URL이 중복된 경우
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            news_log_collection.insert_one(metadata)
            logger.debug(f"메타데이터 저장 성공: {metadata.get('url')}")
            return True
        except DuplicateKeyError:
            logger.debug(f"중복된 URL: {metadata.get('url')}")
            raise
        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")
            return False

    def update_news_metadata(self, url: str, metadata: Dict) -> bool:
        """
        뉴스 메타데이터 업데이트

        Args:
            url: 뉴스 URL
            metadata: 업데이트할 메타데이터

        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            result = news_log_collection.update_one(
                {"url": url},
                {"$set": metadata}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"메타데이터 업데이트 실패: {e}")
            return False

    def get_news_by_url(self, url: str) -> Optional[Dict]:
        """
        URL로 저장된 뉴스 메타데이터 조회

        Args:
            url: 뉴스 URL

        Returns:
            Optional[Dict]: 뉴스 메타데이터 (없으면 None)
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            return news_log_collection.find_one({"url": url})
        except Exception as e:
            logger.error(f"뉴스 조회 실패: {e}")
            return None

    def get_recent_news(self, limit: int = 10) -> List[Dict]:
        """
        최근 저장된 뉴스 목록 조회

        Args:
            limit: 조회할 뉴스 개수

        Returns:
            List[Dict]: 뉴스 메타데이터 리스트
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            cursor = news_log_collection.find().sort("saved_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"최근 뉴스 조회 실패: {e}")
            return []

    def search_news_by_query(self, search_query: str, limit: int = 10) -> List[Dict]:
        """
        검색어로 저장된 뉴스 조회

        Args:
            search_query: 검색어
            limit: 조회할 뉴스 개수

        Returns:
            List[Dict]: 뉴스 메타데이터 리스트
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            cursor = news_log_collection.find(
                {"search_query": search_query}
            ).sort("saved_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"뉴스 검색 실패: {e}")
            return []

    def count_news_metadata(self) -> int:
        """
        저장된 뉴스 메타데이터 개수 조회

        Returns:
            int: 저장된 뉴스 개수
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            return news_log_collection.count_documents({})
        except Exception as e:
            logger.error(f"뉴스 개수 조회 실패: {e}")
            return 0

    def news_exists(self, url: str) -> bool:
        """
        뉴스가 이미 저장되어 있는지 확인

        Args:
            url: 뉴스 URL

        Returns:
            bool: 존재 여부
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            return news_log_collection.count_documents({"url": url}) > 0
        except Exception as e:
            logger.error(f"뉴스 존재 확인 실패: {e}")
            return False

    # ==================== news.raw 컬렉션 (원본 API 데이터) ====================

    def save_raw_news(self, raw_data: Dict) -> bool:
        """
        원본 API 응답 데이터를 news.raw 컬렉션에 저장
        db.getCollection("news.raw").insertOne() 메서드 사용

        Args:
            raw_data: 저장할 원본 데이터

        Returns:
            bool: 저장 성공 여부
        """
        try:
            news_raw_collection = self.db.get_collection("news.raw")
            news_raw_collection.insert_one(raw_data)
            logger.debug(f"원본 데이터 저장 성공: {raw_data.get('url')}")
            return True
        except DuplicateKeyError:
            # 중복이면 업데이트
            try:
                news_raw_collection = self.db.get_collection("news.raw")
                news_raw_collection.update_one(
                    {"url": raw_data.get("url")},
                    {"$set": raw_data}
                )
                logger.debug(f"원본 데이터 업데이트: {raw_data.get('url')}")
                return True
            except Exception as e:
                logger.error(f"원본 데이터 업데이트 실패: {e}")
                return False
        except Exception as e:
            logger.error(f"원본 데이터 저장 실패: {e}")
            return False

    def get_raw_news_by_url(self, url: str) -> Optional[Dict]:
        """
        URL로 원본 뉴스 데이터 조회

        Args:
            url: 뉴스 URL

        Returns:
            Optional[Dict]: 원본 뉴스 데이터 (없으면 None)
        """
        try:
            news_raw_collection = self.db.get_collection("news.raw")
            return news_raw_collection.find_one({"url": url})
        except Exception as e:
            logger.error(f"원본 뉴스 조회 실패: {e}")
            return None

    def count_raw_news(self) -> int:
        """
        저장된 원본 뉴스 데이터 개수 조회

        Returns:
            int: 저장된 원본 뉴스 개수
        """
        try:
            news_raw_collection = self.db.get_collection("news.raw")
            return news_raw_collection.count_documents({})
        except Exception as e:
            logger.error(f"원본 뉴스 개수 조회 실패: {e}")
            return 0

    # ==================== 통계 및 유틸리티 ====================

    def get_collection_stats(self) -> Dict[str, int]:
        """
        컬렉션별 저장된 문서 개수 조회

        Returns:
            Dict: 컬렉션별 문서 개수
        """
        return {
            "news_log_count": self.count_news_metadata(),
            "news_raw_count": self.count_raw_news()
        }

    def delete_news_by_url(self, url: str) -> bool:
        """
        URL로 뉴스 삭제 (metadata + raw)

        Args:
            url: 뉴스 URL

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            news_log_collection = self.db.get_collection("news.log")
            news_raw_collection = self.db.get_collection("news.raw")

            log_result = news_log_collection.delete_one({"url": url})
            raw_result = news_raw_collection.delete_one({"url": url})

            return log_result.deleted_count > 0 or raw_result.deleted_count > 0
        except Exception as e:
            logger.error(f"뉴스 삭제 실패: {e}")
            return False

    def clear_all_news(self):
        """모든 뉴스 데이터 삭제 (개발/테스트용)"""
        try:
            news_log_collection = self.db.get_collection("news.log")
            news_raw_collection = self.db.get_collection("news.raw")

            log_result = news_log_collection.delete_many({})
            raw_result = news_raw_collection.delete_many({})

            logger.info(f"모든 뉴스 삭제 완료 - log: {log_result.deleted_count}, raw: {raw_result.deleted_count}")
            return True
        except Exception as e:
            logger.error(f"뉴스 전체 삭제 실패: {e}")
            return False
