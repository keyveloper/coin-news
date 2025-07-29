"""
ChromaDB 설정 및 클라이언트 관리
"""
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent

# ChromaDB 데이터 저장 경로
CHROMA_DB_PATH = PROJECT_ROOT / "data" / "chroma_db"

# ChromaDB 컬렉션 이름
COLLECTION_NAME = "coin_news"


class ChromaDBClient:
    """ChromaDB 클라이언트 싱글톤"""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaDBClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self):
        """ChromaDB 클라이언트 초기화"""
        # 데이터 디렉토리 생성
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

        # ChromaDB 클라이언트 생성
        self._client = chromadb.PersistentClient(
            path=str(CHROMA_DB_PATH),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        print(f"ChromaDB 클라이언트 초기화 완료: {CHROMA_DB_PATH}")

    def get_client(self):
        """ChromaDB 클라이언트 반환"""
        return self._client

    def get_or_create_collection(self, collection_name: str = COLLECTION_NAME):
        """
        컬렉션 가져오기 또는 생성
        Args:
            collection_name: 컬렉션 이름
        Returns:
            ChromaDB Collection 객체
        """
        collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "코인 뉴스 벡터 저장소"}
        )
        print(f"컬렉션 '{collection_name}' 로드 완료 (문서 수: {collection.count()})")
        return collection

    def reset_collection(self, collection_name: str = COLLECTION_NAME):
        """
        컬렉션 초기화 (모든 데이터 삭제)
        Args:
            collection_name: 컬렉션 이름
        """
        try:
            self._client.delete_collection(name=collection_name)
            print(f"컬렉션 '{collection_name}' 삭제 완료")
        except Exception as e:
            print(f"컬렉션 삭제 실패: {e}")

        # 새로 생성
        return self.get_or_create_collection(collection_name)

    def list_collections(self):
        """모든 컬렉션 목록 반환"""
        collections = self._client.list_collections()
        return [col.name for col in collections]


# 전역 클라이언트 인스턴스
def get_chroma_client() -> ChromaDBClient:
    """ChromaDB 클라이언트 인스턴스 반환"""
    return ChromaDBClient()