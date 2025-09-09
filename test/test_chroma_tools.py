# -*- coding: utf-8 -*-
"""
ChromaDB 연결 및 Vector Tools 테스트
"""
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

def test_chroma_connection():
    """1. ChromaDB 연결 테스트"""
    print("\n" + "="*60)
    print("[TEST 1] ChromaDB Connection")
    print("="*60)

    try:
        from app.config.chroma_config import get_chroma_client, CHROMA_DB_PATH

        print(f"ChromaDB Path: {CHROMA_DB_PATH}")
        print(f"Path exists: {CHROMA_DB_PATH.exists()}")

        client = get_chroma_client()
        chroma_client = client.get_client()

        # List all collections
        collections = chroma_client.list_collections()
        print(f"\nCollections found: {len(collections)}")
        for col in collections:
            print(f"  - {col.name}: {col.count()} documents")

        print("\n[RESULT] ChromaDB connection: SUCCESS")
        return True

    except Exception as e:
        print(f"\n[RESULT] ChromaDB connection: FAILED")
        print(f"Error: {e}")
        return False


def test_news_repository():
    """2. NewsRepository 및 데이터 확인"""
    print("\n" + "="*60)
    print("[TEST 2] NewsRepository Stats")
    print("="*60)

    try:
        from app.repository.news_repository import NewsRepository

        repo = NewsRepository()
        stats = repo.get_stats()

        print(f"Collection: {stats['collection_name']}")
        print(f"Total documents: {stats['total_count']}")

        if stats['total_count'] > 0:
            # 샘플 데이터 조회
            sample = repo.find_all_news(limit=3)
            print(f"\nSample documents ({len(sample)}):")
            for idx, news in enumerate(sample, 1):
                print(f"  {idx}. {news.title[:50]}..." if len(news.title) > 50 else f"  {idx}. {news.title}")

        print("\n[RESULT] NewsRepository: SUCCESS")
        return stats['total_count']

    except Exception as e:
        print(f"\n[RESULT] NewsRepository: FAILED")
        print(f"Error: {e}")
        return 0


def test_semantic_search():
    """3. semantic_search tool 테스트"""
    print("\n" + "="*60)
    print("[TEST 3] semantic_search Tool")
    print("="*60)

    try:
        from app.tools.vector_tools import semantic_search

        # 기본 검색 테스트
        query = "BTC 비트코인 가격"
        print(f"Query: {query}")
        print(f"Parameters: top_k=5, similarity_threshold=0.5")

        # LangChain tool이므로 .func() 또는 invoke() 사용
        if hasattr(semantic_search, 'func'):
            results = semantic_search.func(
                query=query,
                top_k=5,
                similarity_threshold=0.5
            )
        else:
            results = semantic_search(
                query=query,
                top_k=5,
                similarity_threshold=0.5
            )

        print(f"\nResults: {len(results)} documents found")

        if results:
            print("\nTop results:")
            for idx, news in enumerate(results[:3], 1):
                score = f"{news.similarity_score:.3f}" if news.similarity_score else "N/A"
                title = news.title[:60] if news.title else "No title"
                print(f"  {idx}. [{score}] {title}...")

        print("\n[RESULT] semantic_search: SUCCESS")
        return len(results)

    except Exception as e:
        print(f"\n[RESULT] semantic_search: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def test_make_semantic_query():
    """4. make_semantic_query tool 테스트"""
    print("\n" + "="*60)
    print("[TEST 4] make_semantic_query Tool")
    print("="*60)

    try:
        from app.tools.vector_tools import make_semantic_query

        params = {
            "coin_names": ["BTC"],
            "intent_type": "price_reason",
            "event_keywords": ["급등", "상승"],
            "event_magnitude": "surge",
            "custom_context": "10월 중순 가격 변동 원인"
        }

        print(f"Parameters:")
        for k, v in params.items():
            print(f"  {k}: {v}")

        # LangChain tool 호출
        if hasattr(make_semantic_query, 'func'):
            query = make_semantic_query.func(**params)
        else:
            query = make_semantic_query(**params)

        print(f"\nGenerated Query: {query}")
        print("\n[RESULT] make_semantic_query: SUCCESS")
        return query

    except Exception as e:
        print(f"\n[RESULT] make_semantic_query: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_auto_chaining():
    """5. Auto-chaining 테스트 (make_semantic_query -> semantic_search)"""
    print("\n" + "="*60)
    print("[TEST 5] Auto-Chaining (Query Generation -> Search)")
    print("="*60)

    try:
        from app.tools.vector_tools import make_semantic_query, semantic_search

        # Step 1: Generate query
        print("Step 1: Generating query...")
        if hasattr(make_semantic_query, 'func'):
            query = make_semantic_query.func(
                coin_names=["BTC"],
                intent_type="market_trend",
                event_keywords=["시장", "동향"],
                custom_context="최근 시장 트렌드"
            )
        else:
            query = make_semantic_query(
                coin_names=["BTC"],
                intent_type="market_trend",
                event_keywords=["시장", "동향"],
                custom_context="최근 시장 트렌드"
            )

        print(f"  Generated: {query}")

        # Step 2: Search with generated query
        print("\nStep 2: Searching with generated query...")
        if hasattr(semantic_search, 'func'):
            results = semantic_search.func(
                query=query,
                top_k=5,
                similarity_threshold=0.5
            )
        else:
            results = semantic_search(
                query=query,
                top_k=5,
                similarity_threshold=0.5
            )

        print(f"  Found: {len(results)} results")

        if results:
            print("\n  Top 3 results:")
            for idx, news in enumerate(results[:3], 1):
                score = f"{news.similarity_score:.3f}" if news.similarity_score else "N/A"
                title = news.title[:50] if news.title else "No title"
                print(f"    {idx}. [{score}] {title}...")

        print("\n[RESULT] Auto-chaining: SUCCESS")
        return len(results)

    except Exception as e:
        print(f"\n[RESULT] Auto-chaining: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    print("\n" + "#"*60)
    print("# ChromaDB & Vector Tools Test Suite")
    print("#"*60)

    results = {}

    # Test 1: ChromaDB Connection
    results['chroma_connection'] = test_chroma_connection()

    # Test 2: NewsRepository
    results['news_count'] = test_news_repository()

    # Test 3: semantic_search
    results['search_results'] = test_semantic_search()

    # Test 4: make_semantic_query
    results['generated_query'] = test_make_semantic_query()

    # Test 5: Auto-chaining
    results['auto_chain_results'] = test_auto_chaining()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"ChromaDB Connection: {'OK' if results['chroma_connection'] else 'FAILED'}")
    print(f"Documents in DB: {results['news_count']}")
    print(f"Search Results: {results['search_results']}")
    print(f"Query Generation: {'OK' if results['generated_query'] else 'FAILED'}")
    print(f"Auto-chain Results: {results['auto_chain_results']}")

    if results['news_count'] == 0:
        print("\n[WARNING] ChromaDB is empty! No documents to search.")
        print("You may need to populate the database first.")


if __name__ == "__main__":
    main()
