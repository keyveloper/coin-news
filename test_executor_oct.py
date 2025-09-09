# -*- coding: utf-8 -*-
"""
Executor 테스트 - 10월 중순 날짜로 고정
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')


def test_with_october_date():
    """10월 중순 날짜로 전체 파이프라인 테스트"""
    print("\n" + "="*70)
    print("Full Pipeline Test with October 15, 2025")
    print("="*70)

    from app.agent.query_planning_agent import get_query_planning_agent
    from app.agent.executor_agent import get_executor_agent
    from app.schemas.query_plan import QueryPlan, ToolCall

    # 10월 15일 2025년 timestamp (UTC 00:00:00)
    # 2025-10-15 00:00:00 UTC = 1760486400
    OCTOBER_15_2025 = 1760486400

    print(f"\n[Fixed Date]: October 15, 2025 (timestamp: {OCTOBER_15_2025})")

    # ==================== Manual QueryPlan (10월 중순 기준) ====================
    print("\n" + "-"*70)
    print("[Layer 2] QueryPlanner - Manual Plan with October date")
    print("-"*70)

    # NormalizedQuery 시뮬레이션 (10월 중순 비트코인 급등 원인)
    normalized_query = {
        "intent_type": "price_reason",
        "target": {"coin": ["BTC"]},
        "event": {
            "keywords": ["급등", "상승"],
            "magnitude": "big"
        },
        "goal": {"task": "find_reasons", "depth": "medium"},
        "time_range": {
            "pivot_time": "20251015",  # 10월 15일
            "relative": "1m"  # 1개월 범위
        }
    }

    print(f"\n  Simulated NormalizedQuery:")
    print(f"    intent_type: {normalized_query['intent_type']}")
    print(f"    target.coin: {normalized_query['target']['coin']}")
    print(f"    time_range.pivot_time: {normalized_query['time_range']['pivot_time']}")

    planner = get_query_planning_agent()
    query_plan = planner.make_plan(normalized_query)

    print(f"\n  QueryPlan Generated:")
    print(f"    intent_type: {query_plan.intent_type}")
    print(f"    pivot_time: {query_plan.pivot_time}")
    print(f"    total tool_calls: {len(query_plan.query_plan)}")

    print(f"\n  Tool Calls Summary:")
    for idx, tc in enumerate(query_plan.query_plan, 1):
        if tc.tool_name == "make_semantic_query":
            ctx = tc.arguments.get('custom_context', '')
            print(f"    [{idx}] {tc.tool_name} - {ctx}")
        else:
            print(f"    [{idx}] {tc.tool_name}")

    # ==================== Layer 3: Executor ====================
    print("\n" + "-"*70)
    print("[Layer 3] Executor - Execute with tracking")
    print("-"*70)

    from app.tools.vector_tools import make_semantic_query

    # 생성되는 쿼리 추적
    generated_queries = []

    print(f"\n  Generating queries for VectorDB...")
    for idx, tc in enumerate(query_plan.query_plan, 1):
        if tc.tool_name == "make_semantic_query":
            args = tc.arguments
            clean_args = {k: v for k, v in args.items() if not k.startswith("_")}

            if hasattr(make_semantic_query, 'func'):
                query = make_semantic_query.func(**clean_args)
            else:
                query = make_semantic_query(**clean_args)

            generated_queries.append({
                "idx": idx,
                "context": args.get('custom_context'),
                "query": query,
                "search_params": args.get('_search_params', {})
            })

    print(f"\n  Generated Queries for VectorDB:")
    print("  " + "="*60)
    for q in generated_queries:
        print(f"\n    [{q['idx']}] Context: {q['context']}")
        print(f"        Query: \"{q['query']}\"")
        print(f"        top_k: {q['search_params'].get('top_k')}, threshold: {q['search_params'].get('similarity_threshold')}")

    # Execute full plan
    print(f"\n  Executing full plan...")
    executor = get_executor_agent()
    result = executor.do_plan(query_plan)

    print(f"\n  PlanResult:")
    print(f"    total_actions: {result.total_actions}")
    print(f"    successful_actions: {result.successful_actions}")
    print(f"    failed_actions: {result.failed_actions}")
    print(f"    coin_names: {result.coin_names}")
    print(f"    price_data_count: {sum(len(v) for v in result.collected_coin_prices.values())}")
    print(f"    news_chunks_count: {len(result.collected_news_chunks)}")
    print(f"    generated_queries: {len(result.generated_queries)}")

    if result.errors:
        print(f"    errors: {result.errors}")

    # News Results
    if result.collected_news_chunks:
        print(f"\n  Collected News (top 5):")
        for i, chunk in enumerate(result.collected_news_chunks[:5], 1):
            score = f"{chunk.similarity_score:.3f}" if chunk.similarity_score else "N/A"
            title = chunk.title[:45] if chunk.title else "N/A"
            print(f"    [{i}] sim={score} | {title}...")

    # Summaries
    if result.price_summary:
        print(f"\n  Price Summary:")
        print(f"    {result.price_summary[:300]}...")

    if result.news_summary:
        print(f"\n  News Summary:")
        print(f"    {result.news_summary[:300]}...")

    if result.combined_summary:
        print(f"\n  Combined Summary:")
        print(f"    {result.combined_summary[:300]}...")

    # ==================== Final Summary ====================
    print("\n" + "="*70)
    print("FINAL SUMMARY: Queries sent to VectorDB")
    print("="*70)
    for q in generated_queries:
        print(f"\n  [{q['idx']}] \"{q['query']}\"")

    print(f"\n  Total news collected: {len(result.collected_news_chunks)}")


if __name__ == "__main__":
    test_with_october_date()
