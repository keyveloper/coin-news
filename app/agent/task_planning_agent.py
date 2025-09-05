# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from typing import Dict, Optional
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic


class TaskPlanningAgent:
    """
    Task Planning Agent that generates execution plans for cryptocurrency queries.

    This agent uses LLM with DB tools to dynamically create TaskPlans based on intent.
    """
    _instance: Optional["TaskPlanningAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # LLM setup
        model_name = os.getenv("ANTHROPIC_TASK_PLANNER_MODEL_NAME", "claude-3-5-haiku-20241022")
        temperature = float(os.getenv("TEMPERATURE", "0.0"))
        timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "60.0"))

        self.llm = ChatAnthropic(
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            stop=None  # No stop sequences by default
        )

        # Load system prompt
        prompt_dir = Path(__file__).parent.parent / "prompt"
        prompt_file = prompt_dir / "task_planning_agent_system_prompt"
        self.system_prompt = prompt_file.read_text(encoding="utf-8")

        # Register DB tools
        from app.tools.db_tools import (
            search_news_by_semantic_query,
            search_news_by_semantic_query_with_date,
            get_price_week_before,
            get_price_week_after,
            get_price_month_before,
            get_price_month_after,
        )

        self.tools = [
            search_news_by_semantic_query,
            search_news_by_semantic_query_with_date,
            get_price_week_before,
            get_price_week_after,
            get_price_month_before,
            get_price_month_after,
        ]

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        self._initialized = True


    def make_plan(self, query_json: Dict) -> "TaskPlan":
        """
        Generate task execution plan using LLM with tool calling.

        :param query_json: NormalizedQuery as dict
        :return: TaskPlan object with action_plan and analysis_instructions
        :raises: HTTPException if intent_type is "unknown"
        """
        from app.schemas.task_plan import TaskPlan, ToolCall
        # Check for unknown intention
        if query_json.get("intent_type") == "unknown":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "UNKNOWN_INTENT",
                    "message": "Unable to determine user intent. Query analysis failed.",
                    "suggestion": "Please rephrase your query with clearer intent"
                }
            )

        # Create messages for LLM
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Generate a task execution plan for this normalized query:

{json.dumps(query_json, indent=2, ensure_ascii=False)}

Based on the intent_type, call the appropriate tools to create an execution plan.
After calling tools, provide analysis instructions for how to process the results.
"""}
        ]

        # Invoke LLM with tools
        response = self.llm_with_tools.invoke(messages)

        # Extract tool calls
        action_plan = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                action_plan.append(ToolCall(
                    tool_name=tool_call["name"],
                    arguments=tool_call["args"]
                ))

        # Extract analysis instructions from response content
        # Handle both string and list of content blocks
        analysis_instructions = ""
        if response.content:
            if isinstance(response.content, str):
                analysis_instructions = response.content
            elif isinstance(response.content, list):
                # Extract text from content blocks
                text_parts = []
                for block in response.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                analysis_instructions = " ".join(text_parts).strip()

        if not analysis_instructions:
            analysis_instructions = "Process and analyze the retrieved data."

        # Return TaskPlan object
        return TaskPlan(
            intent_type=query_json["intent_type"],
            action_plan=action_plan,
            analysis_instructions=analysis_instructions
        )





def get_task_planning_agent() -> TaskPlanningAgent:
    return TaskPlanningAgent()