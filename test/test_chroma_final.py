# -*- coding: utf-8 -*-
"""
ChromaDB 최종 테스트 - threshold 조정
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def test_with_low_threshold():
    """낮은 threshold로 검색 테스트"""
    print("\n" + "="*60)
    print("Test with Low Similarity Threshold")
    print("="*60)

    from app.tools.vector_tools import semantic_search

    test_cases = [
        {"query": "비트코인", "threshold": 0.1},
        {"query": "비트코인", "threshold": 0.0},
        {"query": "비트코인", "threshold": -0.5},
        {"query": "BTC 가격", "threshold": -0.5},
    ]

    for tc in test_cases:
        print(f"\n  Query: '{tc['query']}', threshold: {tc['threshold']}")

        if hasattr(semantic_search, 'func'):
            results = semantic_search.func(
                query=tc['query'],
                top_k=5,
                similarity_threshold=tc['threshold']
            )
        else:
            results = semantic_search(
                query=tc['query'],
                top_k=5,
                similarity_threshold=tc['threshold']
            )

        print(f"    Results: {len(results)}")
        if results:
            for i, r in enumerate(results[:3], 1):
                score = f"{r.similarity_score:.3f}" if r.similarity_score else "N/A"
                title = r.title[:40] if r.title else "N/A"
                print(f"      [{i}] sim={score}, {title}...")


def check_collection_distance_metric():
    """Collection의 distance metric 확인"""
    print("\n" + "="*60)
    print("Check Collection Distance Metric")
    print("="*60)

    from app.config.chroma_config import get_chroma_client

    client = get_chroma_client().get_client()
    collection = client.get_collection("coin_news")

    # Collection metadata
    print(f"\n  Collection name: {collection.name}")
    print(f"  Collection metadata: {collection.metadata}")

    # ChromaDB default distance is l2 (Euclidean)
    # For cosine similarity, we need distance_fn="cosine" when creating collection
    print("\n  Note: ChromaDB default distance is L2 (Euclidean)")
    print("  For proper similarity scoring, collection should use cosine distance")


def test_executor_agent():
    """ExecutorAgent do_plan 테스트"""
    print("\n" + "="*60)
    print("Test ExecutorAgent.do_plan()")
    print("="*60)

    from app.agent.executor_agent import get_executor_agent
    from app.schemas.query_plan import QueryPlan, ToolCall

    # 간단한 QueryPlan 생성
    query_plan = QueryPlan(
        intent_type="price_reason",
        pivot_time=1731801600,  # 2024-11-17 (데이터가 있는 날짜)
        query_plan=[
            ToolCall(
                tool_name="make_semantic_query",
                arguments={
                    "coin_names": ["BTC"],
                    "intent_type": "price_reason",
                    "event_keywords": ["상승", "급등"],
                    "custom_context": "비트코인 가격 상승",
                    "_search_params": {
                        "top_k": 10,
                        "similarity_threshold": -0.5,  # 낮은 threshold
                        "date_range": "month"
                    }
                }
            )
        ]
    )

    print(f"\n  QueryPlan:")
    print(f"    intent_type: {query_plan.intent_type}")
    print(f"    pivot_time: {query_plan.pivot_time}")
    print(f"    tool_calls: {len(query_plan.query_plan)}")

    try:
        executor = get_executor_agent()
        result = executor.do_plan(query_plan)

        print(f"\n  PlanResult:")
        print(f"    total_actions: {result.total_actions}")
        print(f"    successful_actions: {result.successful_actions}")
        print(f"    failed_actions: {result.failed_actions}")
        print(f"    news_chunks collected: {len(result.collected_news_chunks)}")
        print(f"    generated_queries: {len(result.generated_queries)}")
        print(f"    errors: {result.errors}")

        if result.collected_news_chunks:
            print(f"\n  Sample news chunks:")
            for i, chunk in enumerate(result.collected_news_chunks[:3], 1):
                title = chunk.title[:40] if chunk.title else "N/A"
                print(f"      [{i}] {title}...")

    except Exception as e:
        print(f"\n  Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "#"*60)
    print("# ChromaDB Final Test")
    print("#"*60)

    check_collection_distance_metric()
    test_with_low_threshold()
    test_executor_agent()


if __name__ == "__main__":
    main()
