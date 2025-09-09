# -*- coding: utf-8 -*-
"""Query Analyzer Agent - LangChain 기반 쿼리 분석"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from langchain_anthropic import ChatAnthropic
from langsmith import traceable

from app.schemas.normalized_query import NormalizedQuery

logger = logging.getLogger(__name__)


class QueryAnalyzerAgent:
    """Query Analyzer Agent - LangChain 기반 구조화된 쿼리 추출"""

    _instance: Optional["QueryAnalyzerAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.logger = logging.getLogger(__name__)

        # Model settings
        self.model_name = os.getenv("ANTHROPIC_ANALYZER_MODEL", "claude-3-5-haiku-20241022")
        self.temperature = float(os.getenv("ANALYZER_TEMPERATURE", "0.0"))
        self.timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "30.0"))

        # Load system prompt
        prompt_path = Path(__file__).parent.parent / "prompt" / "query_to_json_system_prompt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt_template = f.read().strip()

        self.max_query_length = 200
        self._initialized = True
        self.logger.info(f"QueryAnalyzerAgent initialized with model: {self.model_name}")

    def _get_llm(self) -> ChatAnthropic:
        """LLM 인스턴스 반환"""
        return ChatAnthropic(
            model_name=self.model_name,
            temperature=self.temperature,
            timeout=self.timeout,
            max_tokens=512
        )

    def _get_formatted_system_prompt(self) -> str:
        """현재 날짜 정보를 시스템 프롬프트에 주입"""
        now = datetime.now()
        return self.system_prompt_template.format(
            current_date=now.strftime("%Y-%m-%d"),
            current_year=now.year,
            last_year=now.year - 1
        )

    @traceable(name="QueryAnalyzer.analyze", run_type="llm")
    def analyze_query(self, query: str) -> Dict:
        """
        사용자 쿼리를 분석하여 NormalizedQuery로 변환

        Args:
            query: 사용자의 자연어 쿼리

        Returns:
            NormalizedQuery dict
        """
        self.logger.info(f"Analyzing query: {query}")

        if len(query) > self.max_query_length:
            raise ValueError(f"Query too long (max {self.max_query_length} characters)")

        llm = self._get_llm()

        # Tool binding with Pydantic schema
        llm_with_tools = llm.bind_tools(
            [NormalizedQuery],
            tool_choice="NormalizedQuery"
        )

        messages = [
            {"role": "system", "content": self._get_formatted_system_prompt()},
            {"role": "user", "content": query}
        ]

        response = llm_with_tools.invoke(messages)

        # Extract tool call result
        if response.tool_calls:
            result = response.tool_calls[0]["args"]
            self.logger.info(f"Parsed result: {result}")

            # Validate with Pydantic
            validated = NormalizedQuery(**result)
            return validated.model_dump()

        raise ValueError("No tool call found in response")


# Backward compatibility alias
QueryAnalyzerService = QueryAnalyzerAgent


def get_query_analyzer_agent() -> QueryAnalyzerAgent:
    """Get QueryAnalyzerAgent singleton instance"""
    return QueryAnalyzerAgent()
