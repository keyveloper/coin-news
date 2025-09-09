# -*- coding: utf-8 -*-
"""
Executor Agent - QueryPlan 실행 및 자동 체이닝

역할:
1. QueryPlan의 tool 호출 순차 실행
2. make_semantic_query → semantic_search 자동 체이닝
3. 수집된 데이터 요약 생성
4. 뉴스로부터 추가 쿼리 추출
5. PlanResult 반환
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict

from langsmith import traceable

from app.schemas.query_plan import QueryPlan
from app.schemas.plan_result import PlanResult
from app.schemas.vector_news import VectorNewsResult
from app.schemas.price import PriceData, PriceHourlyData

# DB Tools
from app.tools.price_tools import get_coin_price
from app.tools.vector_tools import make_semantic_query, semantic_search, extract_queries_from_news

# Summarization Tools
from app.tools.summarize_tools import summarize_price_data, summarize_news_chunks, summarize_combined

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    Executor Agent - QueryPlan 실행 및 자동 체이닝

    핵심 기능:
    - make_semantic_query 실행 후 자동으로 semantic_search 호출
    - _search_params 메타데이터를 사용하여 검색 파라미터 설정
    - 수집된 데이터 요약 및 추가 쿼리 생성
    """

    _instance: Optional["ExecutorAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # Register all tools
        self.db_tools = {
            "get_coin_price": get_coin_price,
            "make_semantic_query": make_semantic_query,
            "semantic_search": semantic_search,
            "extract_queries_from_news": extract_queries_from_news,
        }

        self.summary_tools = {
            "summarize_price_data": summarize_price_data,
            "summarize_news_chunks": summarize_news_chunks,
            "summarize_combined": summarize_combined,
        }

        self.all_tools = {**self.db_tools, **self.summary_tools}

        self._initialized = True
        logger.info(f"ExecutorAgent initialized with {len(self.all_tools)} tools")

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """단일 tool 실행"""
        tool_func = self.all_tools.get(tool_name)
        if not tool_func:
            raise ValueError(f"Tool {tool_name} not found")

        # _search_params는 메타데이터이므로 제거
        clean_args = {k: v for k, v in arguments.items() if not k.startswith("_")}

        # LangChain tool 실행
        if hasattr(tool_func, 'func'):
            return tool_func.func(**clean_args)
        else:
            return tool_func(**clean_args)

    @traceable(name="Executor.do_plan", run_type="chain")
    def do_plan(self, query_plan: QueryPlan) -> PlanResult:
        """
        QueryPlan 실행 - make_semantic_query → semantic_search 자동 체이닝

        Flow:
        1. get_coin_price 실행 → 가격 데이터 수집
        2. make_semantic_query 실행 → 쿼리 생성 → 자동으로 semantic_search 호출
        3. 뉴스에서 추가 쿼리 추출
        4. 수집된 데이터 요약
        5. PlanResult 반환
        """
        logger.info(f"Executing QueryPlan with {len(query_plan.query_plan)} actions")

        # Collections
        collected_coin_prices: Dict[str, List[PriceData]] = defaultdict(list)
        collected_coin_hourly_prices: Dict[str, List[PriceHourlyData]] = defaultdict(list)
        collected_news_chunks: List[VectorNewsResult] = []
        generated_queries: List[str] = []
        executed_queries: List[str] = []  # 실행된 쿼리 추적
        coin_names_set = set()
        errors: List[str] = []

        total_actions = len(query_plan.query_plan)
        successful_actions = 0
        failed_actions = 0

        # ==================== Step 1: Execute QueryPlan with Auto-Chaining ====================
        logger.info("Step 1: Executing QueryPlan with auto-chaining")

        for idx, tool_call in enumerate(query_plan.query_plan):
            tool_name = tool_call.tool_name
            arguments = tool_call.arguments

            logger.info(f"[{idx+1}/{total_actions}] Executing: {tool_name}")

            try:
                # Execute the tool
                result = self._execute_tool(tool_name, arguments)
                successful_actions += 1

                # Process based on tool type
                if tool_name == "get_coin_price":
                    coin_name = arguments.get("coin_name", "UNKNOWN")
                    range_type = arguments.get("range_type", "week")
                    coin_names_set.add(coin_name)

                    if range_type == "hour":
                        collected_coin_hourly_prices[coin_name].extend(result)
                    else:
                        collected_coin_prices[coin_name].extend(result)

                    logger.info(f"Collected {len(result)} price records for {coin_name}")

                elif tool_name == "make_semantic_query":
                    # 쿼리 생성 결과
                    query_string = result
                    executed_queries.append(query_string)
                    logger.info(f"Generated query: {query_string}")

                    # ⭐ 자동 체이닝: semantic_search 호출
                    search_params = arguments.get("_search_params", {})
                    try:
                        search_result = self._execute_tool("semantic_search", {
                            "query": query_string,
                            "top_k": search_params.get("top_k", 15),
                            "similarity_threshold": search_params.get("similarity_threshold", 0.65),
                            "pivot_date": search_params.get("pivot_date"),
                            "date_range": search_params.get("date_range", "month"),
                        })

                        if search_result:
                            collected_news_chunks.extend(search_result)
                            logger.info(f"Auto-chained semantic_search: {len(search_result)} results")

                    except Exception as e:
                        logger.warning(f"Auto-chained semantic_search failed: {e}")

                elif tool_name == "semantic_search":
                    # 직접 호출된 경우
                    if result:
                        collected_news_chunks.extend(result)
                        logger.info(f"Collected {len(result)} news chunks")

            except Exception as e:
                error_msg = f"Error executing {tool_name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                failed_actions += 1

        # ==================== Step 2: Extract Additional Queries ====================
        logger.info("Step 2: Extracting additional queries from news")

        if collected_news_chunks:
            for chunk in collected_news_chunks[:3]:
                try:
                    chunk_dict = chunk.model_dump() if hasattr(chunk, 'model_dump') else chunk
                    title = chunk_dict.get("title", "")
                    document = chunk_dict.get("document", "")

                    if title or document:
                        queries = self._execute_tool("extract_queries_from_news", {
                            "title": title,
                            "document": document
                        })
                        if queries:
                            generated_queries.extend(queries)
                            logger.info(f"Extracted {len(queries)} queries from news")

                except Exception as e:
                    logger.warning(f"Failed to extract queries: {e}")

        # ==================== Step 3: Summarize Price Data ====================
        logger.info("Step 3: Summarizing price data")
        price_summary = None

        if collected_coin_prices or collected_coin_hourly_prices:
            try:
                coin_name = list(coin_names_set)[0] if coin_names_set else "UNKNOWN"

                price_data = []
                if coin_name in collected_coin_prices:
                    price_data = [p.model_dump() if hasattr(p, 'model_dump') else p
                                  for p in collected_coin_prices[coin_name]]
                elif coin_name in collected_coin_hourly_prices:
                    price_data = [p.model_dump() if hasattr(p, 'model_dump') else p
                                  for p in collected_coin_hourly_prices[coin_name]]

                if price_data:
                    price_summary = self._execute_tool("summarize_price_data", {
                        "coin_name": coin_name,
                        "price_data": price_data,
                        "analysis_focus": f"{query_plan.intent_type} 분석"
                    })
                    logger.info(f"Price summary generated: {len(price_summary)} chars")

            except Exception as e:
                logger.error(f"Failed to summarize price data: {e}")
                errors.append(f"Price summary failed: {str(e)}")

        # ==================== Step 4: Summarize News Data ====================
        logger.info("Step 4: Summarizing news data")
        news_summary = None

        if collected_news_chunks:
            try:
                news_data = [chunk.model_dump() if hasattr(chunk, 'model_dump') else chunk
                             for chunk in collected_news_chunks]

                news_summary = self._execute_tool("summarize_news_chunks", {
                    "news_chunks": news_data,
                    "focus_topic": query_plan.intent_type
                })
                logger.info(f"News summary generated: {len(news_summary)} chars")

            except Exception as e:
                logger.error(f"Failed to summarize news: {e}")
                errors.append(f"News summary failed: {str(e)}")

        # ==================== Step 5: Generate Combined Summary ====================
        logger.info("Step 5: Generating combined analysis")
        combined_summary = None

        if price_summary or news_summary:
            try:
                coin_name = list(coin_names_set)[0] if coin_names_set else "UNKNOWN"

                combined_summary = self._execute_tool("summarize_combined", {
                    "coin_name": coin_name,
                    "price_summary": price_summary or "가격 데이터 없음",
                    "news_summary": news_summary or "뉴스 데이터 없음",
                    "user_query": query_plan.intent_type
                })
                logger.info(f"Combined summary generated: {len(combined_summary)} chars")

            except Exception as e:
                logger.error(f"Failed to generate combined summary: {e}")
                errors.append(f"Combined summary failed: {str(e)}")

        # ==================== Return PlanResult ====================
        return PlanResult(
            intent_type=query_plan.intent_type,
            collected_coin_prices=dict(collected_coin_prices),
            collected_coin_hourly_prices=dict(collected_coin_hourly_prices),
            collected_news_chunks=collected_news_chunks,
            coin_names=sorted(list(coin_names_set)),
            price_summary=price_summary,
            news_summary=news_summary,
            combined_summary=combined_summary,
            generated_queries=list(set(generated_queries))[:10],
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            errors=errors
        )


def get_executor_agent() -> ExecutorAgent:
    """Get ExecutorAgent singleton instance"""
    return ExecutorAgent()
