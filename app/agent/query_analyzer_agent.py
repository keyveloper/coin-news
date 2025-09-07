"""Query Analyzer Service - Extract intent, date, coin, event from user queries using Claude"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, cast, Any
from anthropic import Anthropic
from anthropic.types import MessageParam, ToolParam
from langsmith import traceable

from app.schemas.normalized_query import NormalizedQuery

logger = logging.getLogger(__name__)


class QueryAnalyzerService:
    """Query Analyzer Service using Claude for structured extraction"""

    _instance: Optional["QueryAnalyzerService"] = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize QueryAnalyzerService with Claude client"""
        # Only initialize once for singleton
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 1. Logger
        self.logger = logging.getLogger(__name__)

        # 2. Environment variables
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.model_name = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "200"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.0"))

        # 3. External client
        self.client = Anthropic(api_key=self.anthropic_api_key)

        # 4. Load system prompt
        prompt_dir = Path(__file__).parent.parent / "prompt"
        prompt_path = prompt_dir / "query_to_json_system_prompt"

        if not prompt_path.exists():
            self.logger.error(f"Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.system_prompt_template = f.read().strip()
                self.logger.info(f"Loaded system prompt template: {len(self.system_prompt_template)} characters")
        except Exception as e:
            self.logger.error(f"Error loading prompt file: {e}")
            raise

        # 5. Settings
        self.max_query_length = 200

        # 6. Cache
        self._query_cache: Dict[str, dict] = {}

        self._initialized = True
        self.logger.info(f"QueryAnalyzerService initialized with model: {self.model_name}")

    def _get_formatted_system_prompt(self) -> str:
        """현재 날짜 정보를 시스템 프롬프트에 주입"""
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_year = now.year
        last_year = now.year - 1

        return self.system_prompt_template.format(
            current_date=current_date,
            current_year=current_year,
            last_year=last_year
        )

    @traceable(name="QueryAnalyzer.analyze_query", run_type="chain")
    def analyze_query(self, query: str) -> Dict:
        """
        사용자 쿼리를 분석하여 NormalizedQuery로 변환

        LangSmith에서 추적:
        - Input: 원본 쿼리
        - Output: NormalizedQuery (intent_type, target, time_range 등)
        """
        self.logger.info(f"Analyzing query: {query}")

        if len(query) > self.max_query_length:
            raise ValueError(f"Query too long (max {self.max_query_length} characters)")

        # System prompt for tool usage
        messages: list[MessageParam] = [{"role": "user", "content": query}]

        # Convert Pydantic model to tool schema
        tool_schema: ToolParam = {
            "name": "analyze_query",
            "description": "Analyze and extract structured information from a cryptocurrency query",
            "input_schema": cast(Any, NormalizedQuery.model_json_schema()),
        }

        # 현재 날짜 정보를 포함한 시스템 프롬프트
        formatted_prompt = self._get_formatted_system_prompt()
        self.logger.info(f"[DATE DEBUG] Using current_date: {datetime.now().strftime('%Y-%m-%d')}, current_year: {datetime.now().year}")

        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=formatted_prompt,
            messages=messages,
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": "analyze_query"}  # type: ignore
        )

        self.logger.info(f"Claude response: {message}")

        # Extract tool use result
        for content_block in message.content:
            if content_block.type == "tool_use" and content_block.name == "analyze_query":
                result = content_block.input
                self.logger.info(f"Parsed result: {result}")

                # Validate with Pydantic model
                validated = NormalizedQuery(**result)
                return validated.model_dump()

        raise ValueError("No tool use found in response")
