# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from typing import Dict, Optional
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from app.schemas.task_plan import TaskPlan, ToolCall
from datetime import datetime, timezone
# Register DB tools
from app.tools.db_tools import (
    get_price_week_before,
    get_price_week_after,
    get_price_month_before,
    get_price_month_after,
)
from app.tools.vector_tools import (
    generate_search_query_from_context
)


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



        self.tools = [
            generate_search_query_from_context,
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

        # Calculate pivot_time
        pivot_time_str = query_json.get("time_range", {}).get("pivot_time")
        if pivot_time_str == "today" or pivot_time_str is None:
            # Get current date at 00:00:00
            now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            pivot_time = int(now.timestamp())
        else:
            # Parse date string (YYYYMMDD format expected)
            try:
                dt = datetime.strptime(str(pivot_time_str), "%Y%m%d")
                dt = dt.replace(tzinfo=timezone.utc)
                pivot_time = int(dt.timestamp())
            except:
                # Fallback to today
                now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                pivot_time = int(now.timestamp())

        # Create messages for LLM
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Generate a task execution plan for this normalized query:

{json.dumps(query_json, indent=2, ensure_ascii=False)}

**Calculated pivot_time**: {pivot_time} (epoch timestamp for today at 00:00:00)
Use this pivot_time for all spot_date/pivot_date arguments in your tool calls.

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
            pivot_time=pivot_time,
            action_plan=action_plan,
            analysis_instructions=analysis_instructions
        )





def get_task_planning_agent() -> TaskPlanningAgent:
    return TaskPlanningAgent()