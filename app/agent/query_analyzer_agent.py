"""Query Analyzer Service - Extract intent, date, coin, event from user queries using Claude"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional
from anthropic import Anthropic
from anthropic.types import MessageParam

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

        # 4. Load prompts
        self.prompt_dir = Path(__file__).parent.parent / "prompt"

        # 7. Settings
        self.max_query_length = 200

        # 8. Cache
        self._query_cache: Dict[str, dict] = {}

        self._initialized = True
        self.logger.info(f"QueryAnalyzerService initialized with model: {self.model_name}")

    def _load_prompt(self, filename: str) -> str:
        """
        Load prompt from file

        Args:
            filename: Prompt file name

        Returns:
            Prompt content as string
        """
        prompt_path = self.prompt_dir / filename

        if not prompt_path.exists():
            self.logger.error(f"Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self.logger.info(f"Loaded prompt from {filename}: {len(content)} characters")
                return content
        except Exception as e:
            self.logger.error(f"Error loading prompt file {filename}: {e}")
            raise


    def analyze_query(self, query: str) -> Dict:
        self.logger.info(f"Analyzing query: {query}")

        if len(query) > self.max_query_length:
            raise ValueError(f"Query too long (max {self.max_query_length} characters)")

        task_prompt = f"{self._load_prompt('query_to_json_system_prompt')}\n\n{query}"
        self.logger.info(f"final prompt: {task_prompt}")

        messages: list[MessageParam] = [{"role": "user", "content": task_prompt}]

        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=messages
        )

        response_text = message.content[0].text
        self.logger.info(f"Claude response: {response_text}")

        return json.loads(response_text)
