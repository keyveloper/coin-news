# -*- coding: utf-8 -*-
"""
VectorDB 쿼리 테스트 - 날짜 필터 없이
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def test_queries_without_date_filter():
    """날짜 필터 없이 생성된 쿼리로 검색 테스트"""
    print("\n" + "="*70)
    print("Test Queries Without Date Filter")
    print("="*70)

    from app.tools.vector_tools import make_semantic_query, semantic_search

    # 테스트할 쿼리 파라미터들
    test_cases = [
        {
            "coin_names": ["BTC"],
            "intent_type": "price_reason",
            "event_keywords": ["급등", "상승"],
            "custom_context": "직접적인 가격 변동 원인"
        },
        {
            "coin_names": ["BTC"],
            "intent_type": "price_reason",
            "event_keywords": ["ETF", "승인", "기관투자"],
            "custom_context": "호재 이벤트 분석"
        },
        {
            "coin_names": ["BTC"],
            "intent_type": "market_trend",
            "event_keywords": ["시장", "동향"],
            "custom_context": "전반적인 시장 동향"
        }
    ]

    results_summary = []

    for idx, params in enumerate(test_cases, 1):
        print(f"\n[Test {idx}] {params['custom_context']}")
        print("-" * 50)

        # 1. 쿼리 생성
        if hasattr(make_semantic_query, 'func'):
            query = make_semantic_query.func(**params)
        else:
            query = make_semantic_query(**params)

        print(f"  Generated Query: \"{query}\"")

        # 2. 날짜 필터 없이 검색
        if hasattr(semantic_search, 'func'):
            results = semantic_search.func(
                query=query,
                top_k=5,
                similarity_threshold=0.0,
                pivot_date=None,  # 날짜 필터 없음
                date_range=None
            )
        else:
            results = semantic_search(
                query=query,
                top_k=5,
                similarity_threshold=0.0,
                pivot_date=None,
                date_range=None
            )

        print(f"  Results: {len(results)} documents")

        if results:
            print(f"\n  Top Results:")
            for i, r in enumerate(results[:3], 1):
                score = f"{r.similarity_score:.3f}" if r.similarity_score else "N/A"
                title = r.title[:50] if r.title else "N/A"
                print(f"    [{i}] sim={score} | {title}...")

        results_summary.append({
            "context": params['custom_context'],
            "query": query,
            "count": len(results)
        })

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for r in results_summary:
        print(f"\n  Context: {r['context']}")
        print(f"  Query: \"{r['query']}\"")
        print(f"  Results: {r['count']} documents")


if __name__ == "__main__":
    test_queries_without_date_filter()
