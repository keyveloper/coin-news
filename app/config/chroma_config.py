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



# 전역 클라이언트 인스턴스
def get_chroma_client() -> ChromaDBClient:
    """ChromaDB 클라이언트 인스턴스 반환"""
    return ChromaDBClient()