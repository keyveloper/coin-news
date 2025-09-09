# -*- coding: utf-8 -*-
"""
Executor 테스트 - 벡터DB로 넘어가는 쿼리 확인
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')


def test_full_pipeline():
    """QueryAnalyzer -> QueryPlanner -> Executor 전체 파이프라인 테스트"""
    print("\n" + "="*70)
    print("Full Pipeline Test: QueryAnalyzer -> QueryPlanner -> Executor")
    print("="*70)

    from app.agent.query_analyzer_agent import QueryAnalyzerService
    from app.agent.query_planning_agent import get_query_planning_agent
    from app.agent.executor_agent import get_executor_agent

    # Test query
    test_query = "비트코인 최근 가격 상승 원인"
    print(f"\n[Input Query]: {test_query}")

    # ==================== Layer 1: QueryAnalyzer ====================
    print("\n" + "-"*70)
    print("[Layer 1] QueryAnalyzer")
    print("-"*70)

    analyzer = QueryAnalyzerService()
    normalized_query = analyzer.analyze_query(test_query)

    print(f"\n  NormalizedQuery:")
    print(f"    intent_type: {normalized_query.get('intent_type')}")
    print(f"    target.coin: {normalized_query.get('target', {}).get('coin')}")
    print(f"    event.magnitude: {normalized_query.get('event', {}).get('magnitude')}")
    print(f"    event.keywords: {normalized_query.get('event', {}).get('keywords')}")
    print(f"    time_range.pivot_time: {normalized_query.get('time_range', {}).get('pivot_time')}")
    print(f"    goal.depth: {normalized_query.get('goal', {}).get('depth')}")

    # ==================== Layer 2: QueryPlanner ====================
    print("\n" + "-"*70)
    print("[Layer 2] QueryPlanner")
    print("-"*70)

    planner = get_query_planning_agent()
    query_plan = planner.make_plan(normalized_query)

    print(f"\n  QueryPlan:")
    print(f"    intent_type: {query_plan.intent_type}")
    print(f"    pivot_time: {query_plan.pivot_time}")
    print(f"    total tool_calls: {len(query_plan.query_plan)}")

    print(f"\n  Tool Calls:")
    for idx, tc in enumerate(query_plan.query_plan, 1):
        print(f"\n    [{idx}] {tc.tool_name}")
        if tc.tool_name == "make_semantic_query":
            args = tc.arguments
            print(f"        coin_names: {args.get('coin_names')}")
            print(f"        intent_type: {args.get('intent_type')}")
            print(f"        event_keywords: {args.get('event_keywords')}")
            print(f"        custom_context: {args.get('custom_context')}")
            search_params = args.get('_search_params', {})
            print(f"        _search_params:")
            print(f"          top_k: {search_params.get('top_k')}")
            print(f"          similarity_threshold: {search_params.get('similarity_threshold')}")
            print(f"          date_range: {search_params.get('date_range')}")
        elif tc.tool_name == "get_coin_price":
            args = tc.arguments
            print(f"        coin_name: {args.get('coin_name')}")
            print(f"        range_type: {args.get('range_type')}")

    # ==================== Layer 3: Executor ====================
    print("\n" + "-"*70)
    print("[Layer 3] Executor")
    print("-"*70)

    executor = get_executor_agent()

    # 쿼리 생성 결과를 추적하기 위해 직접 실행
    generated_queries = []

    print(f"\n  Executing tool calls and tracking generated queries...")

    from app.tools.vector_tools import make_semantic_query, semantic_search

    for idx, tc in enumerate(query_plan.query_plan, 1):
        if tc.tool_name == "make_semantic_query":
            args = tc.arguments
            clean_args = {k: v for k, v in args.items() if not k.startswith("_")}

            # Generate query
            if hasattr(make_semantic_query, 'func'):
                query = make_semantic_query.func(**clean_args)
            else:
                query = make_semantic_query(**clean_args)

            generated_queries.append({
                "tool_call_idx": idx,
                "custom_context": args.get('custom_context'),
                "generated_query": query,
                "search_params": args.get('_search_params', {})
            })

    print(f"\n  Generated Queries for VectorDB:")
    print("  " + "="*60)
    for q in generated_queries:
        print(f"\n    [{q['tool_call_idx']}] Context: {q['custom_context']}")
        print(f"        Query -> VectorDB: \"{q['generated_query']}\"")
        print(f"        top_k: {q['search_params'].get('top_k')}")
        print(f"        threshold: {q['search_params'].get('similarity_threshold')}")

    # Execute full plan
    print(f"\n  Executing full plan...")
    result = executor.do_plan(query_plan)

    print(f"\n  PlanResult:")
    print(f"    total_actions: {result.total_actions}")
    print(f"    successful_actions: {result.successful_actions}")
    print(f"    failed_actions: {result.failed_actions}")
    print(f"    coin_names: {result.coin_names}")
    print(f"    collected_news_chunks: {len(result.collected_news_chunks)}")
    print(f"    generated_queries: {len(result.generated_queries)}")

    if result.collected_news_chunks:
        print(f"\n  Sample News Results (top 5):")
        for i, chunk in enumerate(result.collected_news_chunks[:5], 1):
            score = f"{chunk.similarity_score:.3f}" if chunk.similarity_score else "N/A"
            title = chunk.title[:50] if chunk.title else "N/A"
            print(f"      [{i}] sim={score} | {title}...")

    if result.price_summary:
        print(f"\n  Price Summary: {result.price_summary[:200]}...")

    if result.news_summary:
        print(f"\n  News Summary: {result.news_summary[:200]}...")

    if result.combined_summary:
        print(f"\n  Combined Summary: {result.combined_summary[:200]}...")

    if result.errors:
        print(f"\n  Errors: {result.errors}")

    # ==================== Summary ====================
    print("\n" + "="*70)
    print("SUMMARY: Queries sent to VectorDB")
    print("="*70)
    for q in generated_queries:
        print(f"\n  [{q['tool_call_idx']}] \"{q['generated_query']}\"")


if __name__ == "__main__":
    test_full_pipeline()
