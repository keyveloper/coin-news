# -*- coding: utf-8 -*-
"""
ChromaDB 검색 디버깅
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def debug_chroma_search():
    """ChromaDB 직접 검색 테스트"""
    print("\n" + "="*60)
    print("ChromaDB Direct Debug")
    print("="*60)

    from app.config.chroma_config import get_chroma_client
    from langchain_openai import OpenAIEmbeddings

    client = get_chroma_client().get_client()
    collection = client.get_collection("coin_news")

    # 1. Collection info
    print(f"\n[1] Collection Stats")
    print(f"  Count: {collection.count()}")

    # 2. Get sample documents with metadata
    print(f"\n[2] Sample Documents (first 5)")
    sample = collection.get(limit=5, include=['documents', 'metadatas', 'embeddings'])

    for idx in range(min(5, len(sample['ids']))):
        doc_id = sample['ids'][idx]
        doc = sample['documents'][idx] if sample['documents'] else "N/A"
        meta = sample['metadatas'][idx] if sample['metadatas'] else {}
        has_embedding = sample['embeddings'] is not None and len(sample['embeddings']) > idx

        print(f"\n  [{idx+1}] ID: {doc_id[:30]}...")
        print(f"      Document: {doc[:80]}..." if doc and len(doc) > 80 else f"      Document: {doc}")
        print(f"      Title: {meta.get('title', 'N/A')[:60]}...")
        print(f"      Has Embedding: {has_embedding}")
        print(f"      Metadata keys: {list(meta.keys())}")

    # 3. Check metadata structure
    print(f"\n[3] Metadata Structure Check")
    if sample['metadatas']:
        meta = sample['metadatas'][0]
        print(f"  Keys: {list(meta.keys())}")
        for k, v in meta.items():
            print(f"    {k}: {type(v).__name__} = {str(v)[:50]}...")

    # 4. Direct embedding search test
    print(f"\n[4] Direct Embedding Search Test")
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

    # Test queries
    test_queries = [
        "BTC",
        "비트코인",
        "bitcoin price",
        "ETF",
        "암호화폐"
    ]

    for query in test_queries:
        print(f"\n  Query: '{query}'")
        query_embedding = embedding_model.embed_query(query)

        # Search without where filter
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )

        if results['ids'] and results['ids'][0]:
            print(f"    Found: {len(results['ids'][0])} results")
            for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0])):
                similarity = 1 - dist
                print(f"      [{i+1}] sim={similarity:.3f}, doc={doc[:50] if doc else 'N/A'}...")
        else:
            print(f"    Found: 0 results")

    # 5. Check date range in metadata
    print(f"\n[5] Date Range in Metadata")
    all_docs = collection.get(limit=100, include=['metadatas'])
    dates = []
    for meta in all_docs['metadatas']:
        if 'publish_date' in meta:
            dates.append(meta['publish_date'])

    if dates:
        print(f"  Sample publish_dates: {dates[:5]}")
        print(f"  Min date: {min(dates)}")
        print(f"  Max date: {max(dates)}")
    else:
        print(f"  No publish_date field found in metadata!")
        if all_docs['metadatas']:
            print(f"  Available fields: {list(all_docs['metadatas'][0].keys())}")


if __name__ == "__main__":
    debug_chroma_search()
