# -*- coding: utf-8 -*-
"""Executor Agent - Executes TaskPlan by calling DB tools"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict
import json

from langchain_anthropic import ChatAnthropic

from app.schemas.task_plan import TaskPlan
from app.schemas.plan_result import PlanResult
from app.schemas.vector_news import VectorNewsResult
from app.schemas.price import PriceData, PriceHourlyData
from app.tools.db_tools import (
    search_news_by_semantic_query,
    search_news_by_semantic_query_with_date,
    get_price_by_hour_range,
    get_price_by_oneday,
    get_price_week_before,
    get_price_week_after,
    get_price_month_before,
    get_price_month_after,
    get_price_year,
    get_all_price_by_coin,
)
from app.tools.vector_tools import embed_search_query

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    Executor Agent that executes TaskPlans by calling database tools.

    Takes a TaskPlan with action_plan and executes each tool call sequentially,
    collecting results for the response agent.
    """

    _instance: Optional["ExecutorAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # Initialize LLM with tool binding
        model_name = os.getenv("ANTHROPIC_TASK_EXECUTOR_MODEL_NAME", "claude-3-5-haiku-20241022")
        temperature = float(os.getenv("TEMPERATURE", "0.0"))
        timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "60.0"))

        self.llm = ChatAnthropic(
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            stop=None
        )

        # Load system prompt
        prompt_dir = Path(__file__).parent.parent / "prompt"
        prompt_file = prompt_dir / "executor_agent_system_prompt"
        if prompt_file.exists():
            self.system_prompt = prompt_file.read_text(encoding="utf-8")
            logger.info(f"Loaded executor system prompt: {len(self.system_prompt)} characters")
        else:
            self.system_prompt = ""
            logger.warning("Executor system prompt not found")

        # Register all DB tools
        self.tools = [
            search_news_by_semantic_query,
            search_news_by_semantic_query_with_date,
            get_price_by_hour_range,
            get_price_by_oneday,
            get_price_week_before,
            get_price_week_after,
            get_price_month_before,
            get_price_month_after,
            get_price_year,
            get_all_price_by_coin,
            embed_search_query,
        ]

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        self._initialized = True
        logger.info("ExecutorAgent initialized with LLM and tools")

    def do_plan(self, task_plan: TaskPlan) -> PlanResult:
        """
        Execute TaskPlan by having the agent call tools based on action_plan.

        :param task_plan: TaskPlan with action_plan and analysis_instructions
        :return: PlanResult with structured collected data
        """
        logger.info(f"Executing TaskPlan with {len(task_plan.action_plan)} actions")

        # Collections for structured data
        collected_coin_prices: Dict[str, List[PriceData]] = defaultdict(list)
        collected_coin_hourly_prices: Dict[str, List[PriceHourlyData]] = defaultdict(list)
        collected_news_chunks: List[VectorNewsResult] = []
        coin_names_set = set()
        errors: List[str] = []

        total_actions = len(task_plan.action_plan)
        successful_actions = 0
        failed_actions = 0

        # Build execution context with action plan
        execution_context = {
            "intent_type": task_plan.intent_type,
            "analysis_instructions": task_plan.analysis_instructions,
            "action_plan": [
                {
                    "tool_name": tool_call.tool_name,
                    "arguments": tool_call.arguments
                }
                for tool_call in task_plan.action_plan
            ]
        }

        # Create agent message to execute the plan
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Execute the following TaskPlan:

{json.dumps(execution_context, indent=2, ensure_ascii=False)}

Execute each tool in the action_plan sequentially.
For semantic search tools requiring query_embedding:
1. Use embed_search_query tool to generate embedding from analysis_instructions
2. Then call the search tool with the generated embedding

Return all collected results."""}
        ]

        try:
            # Agent execution loop - let agent call tools automatically
            while True:
                # Invoke agent with tools
                response = self.llm_with_tools.invoke(messages)

                # Check if agent made tool calls
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(f"Agent made {len(response.tool_calls)} tool calls")

                    # Execute each tool call
                    tool_messages = []
                    for idx, tool_call in enumerate(response.tool_calls):
                        tool_name = tool_call["name"]
                        arguments = tool_call["args"]

                        logger.info(f"[{idx+1}/{len(response.tool_calls)}] Executing tool: {tool_name}")

                        try:
                            # Find the tool function
                            tool_func = None
                            for tool in self.tools:
                                if hasattr(tool, 'name') and tool.name == tool_name:
                                    tool_func = tool
                                    break

                            if not tool_func:
                                error_msg = f"Tool {tool_name} not found"
                                logger.error(error_msg)
                                errors.append(error_msg)
                                failed_actions += 1
                                tool_messages.append({
                                    "role": "tool",
                                    "content": json.dumps({"error": error_msg}),
                                    "tool_call_id": tool_call.get("id", "")
                                })
                                continue

                            # Execute tool
                            if hasattr(tool_func, 'func'):
                                result = tool_func.func(**arguments)
                            else:
                                result = tool_func(**arguments)

                            logger.info(f"Tool {tool_name} executed successfully")
                            successful_actions += 1

                            # Process result based on tool type
                            if tool_name.startswith("search_news"):
                                # News search results - VectorNewsResult objects
                                collected_news_chunks.extend(result)

                            elif tool_name == "get_price_by_hour_range":
                                # Hourly price data - PriceHourlyData objects
                                coin_name = arguments.get("coin_name", "UNKNOWN")
                                coin_names_set.add(coin_name)
                                collected_coin_hourly_prices[coin_name].extend(result)

                            elif tool_name.startswith("get_price"):
                                # Daily price data - PriceData objects
                                coin_name = arguments.get("coin_name", "UNKNOWN")
                                coin_names_set.add(coin_name)
                                collected_coin_prices[coin_name].extend(result)

                            # Add tool result to messages for next iteration
                            tool_messages.append({
                                "role": "tool",
                                "content": json.dumps({"success": True, "result_count": len(result) if isinstance(result, list) else 1}),
                                "tool_call_id": tool_call.get("id", "")
                            })

                        except Exception as e:
                            error_msg = f"Error executing {tool_name}: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            errors.append(error_msg)
                            failed_actions += 1

                            tool_messages.append({
                                "role": "tool",
                                "content": json.dumps({"error": error_msg}),
                                "tool_call_id": tool_call.get("id", "")
                            })

                    # Add assistant message with tool calls
                    messages.append({"role": "assistant", "content": response.content or "", "tool_calls": response.tool_calls})

                    # Add tool results
                    messages.extend(tool_messages)

                else:
                    # No more tool calls - agent is done
                    logger.info("Agent execution completed")
                    break

        except Exception as e:
            error_msg = f"Error during agent execution: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            failed_actions = total_actions

        return PlanResult(
            intent_type=task_plan.intent_type,
            collected_coin_prices=dict(collected_coin_prices),
            collected_coin_hourly_prices=dict(collected_coin_hourly_prices),
            collected_news_chunks=collected_news_chunks,
            coin_names=sorted(list(coin_names_set)),
            analysis_instructions=task_plan.analysis_instructions,
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            errors=errors
        )


def get_executor_agent() -> ExecutorAgent:
    """Get ExecutorAgent singleton instance"""
    return ExecutorAgent()
