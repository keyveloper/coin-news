# -*- coding: utf-8 -*-
"""Redis Configuration"""
import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 클라이언트 싱글톤"""

    _instance: Optional["RedisClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.host = os.getenv("REDIS_HOST", "59.187.219.45")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.session_ttl = int(os.getenv("SESSION_TTL", "3600"))

        self._client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
            socket_timeout=5
        )

        self._initialized = True
        logger.info(f"RedisClient initialized: {self.host}:{self.port}")

    @property
    def client(self) -> redis.Redis:
        return self._client

    def ping(self) -> bool:
        """연결 테스트"""
        try:
            return self._client.ping()
        except redis.ConnectionError:
            return False


class SessionManager:
    """채팅 세션 관리자"""

    def __init__(self):
        self.redis = RedisClient().client
        self.ttl = int(os.getenv("SESSION_TTL", "3600"))

    def _session_key(self, session_id: str) -> str:
        return f"chat:session:{session_id}"

    def _messages_key(self, session_id: str) -> str:
        return f"chat:messages:{session_id}"

    def create_session(self, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """새 세션 생성"""
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "context": {}
        }

        key = self._session_key(session_id)
        self.redis.set(key, json.dumps(session_data), ex=self.ttl)
        logger.info(f"Session created: {session_id}")

        return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 조회"""
        key = self._session_key(session_id)
        data = self.redis.get(key)

        if data:
            # TTL 갱신
            self.redis.expire(key, self.ttl)
            return json.loads(data)
        return None

    def update_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """세션 컨텍스트 업데이트"""
        session = self.get_session(session_id)
        if not session:
            return False

        session["context"].update(context)
        session["updated_at"] = datetime.utcnow().isoformat()

        key = self._session_key(session_id)
        self.redis.set(key, json.dumps(session), ex=self.ttl)
        return True

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """메시지 추가"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }

        key = self._messages_key(session_id)
        self.redis.rpush(key, json.dumps(message))
        self.redis.expire(key, self.ttl)

        return True

    def get_messages(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """메시지 히스토리 조회"""
        key = self._messages_key(session_id)
        messages = self.redis.lrange(key, -limit, -1)

        return [json.loads(m) for m in messages]

    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        session_key = self._session_key(session_id)
        messages_key = self._messages_key(session_id)

        self.redis.delete(session_key, messages_key)
        logger.info(f"Session deleted: {session_id}")
        return True


def get_redis_client() -> RedisClient:
    """RedisClient 싱글톤 반환"""
    return RedisClient()


def get_session_manager() -> SessionManager:
    """SessionManager 인스턴스 반환"""
    return SessionManager()
