"""MongoDB 연결 및 관리 모듈"""
import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection


class MongoDBClient:
    """MongoDB 데이터베이스 클라이언트"""

    def __init__(
        self,
        uri: Optional[str] = None,
        database_name: Optional[str] = None
    ):
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE", "coin_news")

        self.client: MongoClient = MongoClient(self.uri)
        self.db: Database = self.client[self.database_name]

    def ping(self) -> bool:
        """MongoDB 연결 확인"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def get_collection(self, collection_name: str) -> Collection:
        """컬렉션 가져오기"""
        return self.db[collection_name]

    def close(self):
        """연결 종료"""
        try:
            self.client.close()
        except Exception:
            pass