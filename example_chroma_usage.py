"""
ChromaDB 사용 예제
"""
from app.repository.chroma_operations import ChromaNewsDB
from app.crawlers.coinness_crawler import CoinNewsCrawler


def example_crawl_and_save():
    """크롤링 후 ChromaDB에 저장하는 예제"""
    print("=" * 50)
    print("1. 뉴스 크롤링 시작")
    print("=" * 50)

    # 크롤러로 뉴스 가져오기
    crawler = CoinNewsCrawler()
    news_data = crawler.crawl()

    print(f"\n크롤링된 뉴스 개수: {len(news_data)}개\n")

    # ChromaDB에 저장
    print("=" * 50)
    print("2. ChromaDB에 저장")
    print("=" * 50)

    db = ChromaNewsDB()
    added_count = db.add_news(news_data)

    print(f"\n총 {added_count}개 뉴스 저장 완료")
    print(f"DB 통계: {db.get_stats()}\n")


def example_search():
    """뉴스 검색 예제"""
    print("=" * 50)
    print("뉴스 검색 예제")
    print("=" * 50)

    db = ChromaNewsDB()

    # 검색어
    query = "비트코인"
    print(f"\n검색어: '{query}'")

    # 유사 뉴스 검색
    results = db.search_news(query, n_results=5)

    print(f"\n검색 결과 ({len(results)}개):")
    for idx, news in enumerate(results, 1):
        print(f"\n{idx}. {news['title']}")
        print(f"   URL: {news['url']}")
        print(f"   생성일: {news['created_at']}")
        if news.get('distance'):
            print(f"   유사도 거리: {news['distance']:.4f}")


def example_get_all():
    """전체 뉴스 조회 예제"""
    print("=" * 50)
    print("전체 뉴스 조회")
    print("=" * 50)

    db = ChromaNewsDB()
    all_news = db.get_all_news(limit=10)

    print(f"\n총 {db.count()}개 중 {len(all_news)}개 조회:\n")
    for idx, news in enumerate(all_news, 1):
        print(f"{idx}. {news['title']}")
        print(f"   {news['url']}\n")


if __name__ == "__main__":
    # 예제 실행
    print("\n" + "=" * 50)
    print("ChromaDB 사용 예제")
    print("=" * 50 + "\n")

    # 1. 크롤링 & 저장
    example_crawl_and_save()

    # 2. 검색
    example_search()

    # 3. 전체 조회
    example_get_all()
