# -*- coding: utf-8 -*-
"""Executor Agent - Executes QueryPlan by calling DB tools"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict
import json

from langchain_anthropic import ChatAnthropic
from langsmith import traceable

from app.schemas.query_plan import QueryPlan
from app.schemas.plan_result import PlanResult
from app.schemas.vector_news import VectorNewsResult
from app.schemas.price import PriceData, PriceHourlyData
from app.tools.price_tools import get_coin_price
from app.tools.vector_tools import make_semantic_query, semantic_search

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    Executor Agent that executes QueryPlans by calling database tools.

    Takes a QueryPlan with query_plan and executes each tool call sequentially,
    collecting results for the response agent.

    Available Tools:
    - get_coin_price: 가격 데이터 조회
    - make_semantic_query: 시맨틱 쿼리 생성
    - semantic_search: 시맨틱 뉴스 검색
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

        # Register DB tools
        # - get_coin_price: 가격 데이터 조회
        # - make_semantic_query: 시맨틱 쿼리 생성
        # - semantic_search: 시맨틱 뉴스 검색 (embedding 내부 처리)
        self.tools = [
            get_coin_price,
            make_semantic_query,
            semantic_search,
        ]

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        self._initialized = True
        logger.info("ExecutorAgent initialized with LLM and tools")

    @traceable(name="Executor.do_plan", run_type="chain")
    def do_plan(self, query_plan: QueryPlan) -> PlanResult:
        """
        Execute QueryPlan by having the agent call tools based on query_plan.

        LangSmith에서 추적:
        - Input: QueryPlan (tool_name, arguments 리스트)
        - Output: PlanResult (prices, news, execution stats)
        - 각 tool 호출 결과 확인 가능

        :param query_plan: QueryPlan with tool call specifications
        :return: PlanResult with structured collected data
        """
        logger.info(f"Executing QueryPlan with {len(query_plan.query_plan)} actions")

        # Collections for structured data
        collected_coin_prices: Dict[str, List[PriceData]] = defaultdict(list)
        collected_coin_hourly_prices: Dict[str, List[PriceHourlyData]] = defaultdict(list)
        collected_news_chunks: List[VectorNewsResult] = []
        coin_names_set = set()
        errors: List[str] = []

        total_actions = len(query_plan.query_plan)
        successful_actions = 0
        failed_actions = 0

        # Build execution context with query plan
        execution_context = {
            "intent_type": query_plan.intent_type,
            "pivot_time": query_plan.pivot_time,
            "query_plan": [
                {
                    "tool_name": tool_call.tool_name,
                    "arguments": tool_call.arguments
                }
                for tool_call in query_plan.query_plan
            ]
        }

        # Create agent message to execute the plan
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Execute the following QueryPlan:

{json.dumps(execution_context, indent=2, ensure_ascii=False)}

Execute each tool in the query_plan sequentially.
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
                            if tool_name == "semantic_search":
                                # News search results - VectorNewsResult objects
                                collected_news_chunks.extend(result)

                            elif tool_name == "get_coin_price":
                                # 통합 가격 조회 tool 결과 처리
                                coin_name = arguments.get("coin_name", "UNKNOWN")
                                range_type = arguments.get("range_type", "week")
                                coin_names_set.add(coin_name)

                                if range_type == "hour":
                                    # Hourly price data - PriceHourlyData objects
                                    collected_coin_hourly_prices[coin_name].extend(result)
                                else:
                                    # Daily price data - PriceData objects
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
            intent_type=query_plan.intent_type,
            collected_coin_prices=dict(collected_coin_prices),
            collected_coin_hourly_prices=dict(collected_coin_hourly_prices),
            collected_news_chunks=collected_news_chunks,
            coin_names=sorted(list(coin_names_set)),
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            errors=errors
        )


def get_executor_agent() -> ExecutorAgent:
    """Get ExecutorAgent singleton instance"""
    return ExecutorAgent()
