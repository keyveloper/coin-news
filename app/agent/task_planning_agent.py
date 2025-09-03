# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from app.tools.tools import *


class TaskPlanningAgent:
    _instance: Optional["TaskPlanningAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o") # 모델 등록 필요
        self.temperature = float(os.getenv("TEMPERATURE", "0.0"))

        self.llm = ChatOpenAI(model=self.model_name, temperature=self.temperature)

        # system prompt 등록
        self.prompt_dir = Path(__file__).parent / "prompt"
        self.system_prompt_file = self.prompt_dir / "task_planning_agent_system_prompt"

        # !!!! error 제어 !!!!
        self.system_prompt = self.system_prompt_file.read_text()

        # tool 등록
        self.tools = [analyze_query]

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )

        self._initialized = True


    def make_plan(self, query_json: Dict) -> Dict:
        """
        1.
        :param query_json:
        :return:
        """
        similarity_threshold = 0
        time_range = 0
        coin_names = query_json["target"]["coin"]





def get_task_planning_agent() -> TaskPlanningAgent:
    return TaskPlanningAgent()