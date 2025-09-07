# -*- coding: utf-8 -*-
"""
LangSmith Configuration - Tracing and Observability Setup
"""
import os
import logging

logger = logging.getLogger(__name__)


def setup_langsmith():
    """
    LangSmith 트레이싱 설정

    환경변수:
    - LANGSMITH_TRACING: true/false
    - LANGSMITH_API_KEY: API 키
    - LANGSMITH_PROJECT: 프로젝트 이름
    - LANGSMITH_ENDPOINT: API 엔드포인트 (선택)
    """
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

    if tracing_enabled:
        api_key = os.getenv("LANGSMITH_API_KEY")
        if not api_key:
            logger.warning("LANGSMITH_TRACING is enabled but LANGSMITH_API_KEY is not set")
            return False

        project = os.getenv("LANGSMITH_PROJECT", "coin-news-agent")
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

        # LangChain 환경변수 설정
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = project
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

        logger.info(f"LangSmith tracing enabled - Project: {project}")
        return True
    else:
        logger.info("LangSmith tracing disabled")
        return False


def is_tracing_enabled() -> bool:
    """트레이싱 활성화 여부 확인"""
    return os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
