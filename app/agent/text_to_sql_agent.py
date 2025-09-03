from typing import Optional
import logging
import os

class Text2SqlService:
    _instance: Optional["Text2SqlService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return


        self.logger = logging.getLogger(__name__)

        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            return ValueError("ANTHROPIC_API_KEY not set")
