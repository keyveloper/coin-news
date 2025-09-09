"""Test script for QueryAnalyzerService"""
import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agent.query_analyzer_agent import QueryAnalyzerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_query_analyzer():
    """Test the QueryAnalyzerService with various queries"""

    print("=" * 80)
    print("Testing QueryAnalyzerService")
    print("=" * 80)

    # Initialize service
    try:
        service = QueryAnalyzerService()
        print("[OK] Service initialized successfully\n")
    except Exception as e:
        print(f"[ERROR] Failed to initialize service: {e}")
        return

    # Test queries
    test_queries = [
        "2024년 12월 비트코인 가격이 떨어졌는데 어떤 이슈가 있었나?",
        "최근 트럼프 대통령의 언급과 비트코인 상관관계를 분석하라",
        "어제 이더리움 뉴스 찾아줘",
        "지난주 BTC 가격 하락 이유를 분석해줘",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Test {i}: {query}")
        print('=' * 80)

        try:
            result = service.analyze_query(query)

            print("\n[RESULT] Analysis Result:")
            print(f"  Intent: {result.get('intent')}")
            print(f"  Date: {result.get('date')}")
            print(f"  Date Epoch: {result.get('date_epoch')}")
            print(f"  Coin: {result.get('coin')}")
            print(f"  Event: {result.get('event')}")
            print(f"  Keywords: {result.get('keywords')}")
            print(f"  Token Usage: {result.get('token_usage')}")
            print(f"\n[OK] Test {i} passed")

        except Exception as e:
            print(f"\n[ERROR] Test {i} failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("Testing complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_query_analyzer()
