"""
MongoDB 설정 및 클라이언트 관리
"""
import os
from pathlib import Path
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Optional

# MongoDB 연결 설정
MONGODB_HOST = "localhost"
MONGODB_PORT = 27017
MONGODB_URL = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/"

# 데이터베이스 및 컬렉션 이름
DATABASE_NAME = "coin_news"
COLLECTION_NAME = "news_metadata"
RAW_COLLECTION_NAME = "news_raw"


class MongoDBClient:
    """MongoDB 클라이언트 싱글톤"""

    _instance = None
    _client: Optional[MongoClient] = None
    _database: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self):
        """MongoDB 클라이언트 초기화"""
        try:
            self._client = MongoClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=5000,  # 5초 타임아웃
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            # 연결 테스트
            self._client.admin.command('ping')
            self._database = self._client[DATABASE_NAME]
            print(f"MongoDB 클라이언트 초기화 완료: {MONGODB_URL}")
            print(f"데이터베이스: {DATABASE_NAME}")
        except Exception as e:
            print(f"MongoDB 연결 실패: {e}")
            raise

    def get_client(self) -> MongoClient:
        """MongoDB 클라이언트 반환"""
        return self._client

    def get_database(self, db_name: str = DATABASE_NAME) -> Database:
        """
        데이터베이스 반환

        Args:
            db_name: 데이터베이스 이름

        Returns:
            Database 객체
        """
        return self._client[db_name]

    def get_collection(self, collection_name: str = COLLECTION_NAME) -> Collection:
        """
        컬렉션 반환

        Args:
            collection_name: 컬렉션 이름

        Returns:
            Collection 객체
        """
        return self._database[collection_name]

    def get_metadata_collection(self) -> Collection:
        """뉴스 메타데이터 컬렉션 반환"""
        return self.get_collection(COLLECTION_NAME)

    def get_raw_collection(self) -> Collection:
        """뉴스 원본 데이터 컬렉션 반환"""
        return self.get_collection(RAW_COLLECTION_NAME)

    def create_indexes(self):
        """
        컬렉션 인덱스 생성
        - url을 유니크 인덱스로 생성하여 중복 방지
        - published_date 인덱스로 날짜별 조회 성능 향상
        """
        metadata_collection = self.get_metadata_collection()
        raw_collection = self.get_raw_collection()

        # 메타데이터 컬렉션 인덱스
        metadata_collection.create_index("url", unique=True)
        metadata_collection.create_index("published_date")
        metadata_collection.create_index("title")

        # 원본 데이터 컬렉션 인덱스
        raw_collection.create_index("url", unique=True)
        raw_collection.create_index("fetched_at")

        print("MongoDB 인덱스 생성 완료")

    def drop_collection(self, collection_name: str):
        """
        컬렉션 삭제

        Args:
            collection_name: 삭제할 컬렉션 이름
        """
        try:
            self._database.drop_collection(collection_name)
            print(f"컬렉션 '{collection_name}' 삭제 완료")
        except Exception as e:
            print(f"컬렉션 삭제 실패: {e}")

    def list_collections(self):
        """모든 컬렉션 목록 반환"""
        return self._database.list_collection_names()

    def get_collection_stats(self, collection_name: str = COLLECTION_NAME):
        """
        컬렉션 통계 반환

        Args:
            collection_name: 컬렉션 이름

        Returns:
            dict: 컬렉션 통계 정보
        """
        collection = self.get_collection(collection_name)
        return {
            "name": collection_name,
            "count": collection.count_documents({}),
            "indexes": list(collection.list_indexes())
        }

    def close(self):
        """MongoDB 연결 종료"""
        if self._client:
            self._client.close()
            print("MongoDB 연결 종료")


# 전역 클라이언트 인스턴스
def get_mongodb_client() -> MongoDBClient:
    """MongoDB 클라이언트 인스턴스 반환"""
    return MongoDBClient()
