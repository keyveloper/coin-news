"""뉴스 API 연동 및 MongoDB 저장 테스트"""
from app.services.news_api import NewsAPIClient
from app.db.mongodb_client import MongoDBClient
from app.repository.news_repository import NewsRepository


def test_news_api():
    """News API 연동 테스트"""
    print("=== News API 테스트 ===")
    client = NewsAPIClient()
    articles = client.get_everything(query="bitcoin", page_size=5)
    print(f"가져온 뉴스 개수: {len(articles)}")
    if articles:
        print(f"첫 번째 뉴스 제목: {articles[0]['title']}")
    print()
    return articles


def test_mongodb_connection():
    """MongoDB 연결 테스트"""
    print("=== MongoDB 연결 테스트 ===")
    mongodb_client = MongoDBClient()
    is_connected = mongodb_client.ping()
    print(f"MongoDB 연결 상태: {'성공' if is_connected else '실패'}")
    print()
    return mongodb_client


def test_save_news(articles, mongodb_client):
    """뉴스 저장 테스트"""
    print("=== 뉴스 저장 테스트 ===")
    repo = NewsRepository(mongodb_client)
    saved_count = repo.save_articles(articles)
    print(f"저장된 뉴스 개수: {saved_count}/{len(articles)}")
    print()
    return repo


def test_retrieve_news(repo):
    """뉴스 조회 테스트"""
    print("=== 뉴스 조회 테스트 ===")
    all_articles = repo.get_all_articles()
    print(f"DB에 저장된 총 뉴스 개수: {len(all_articles)}")
    if all_articles:
        print(f"조회된 뉴스 제목 예시: {all_articles[0]['title']}")
    print()


if __name__ == "__main__":
    try:
        articles = test_news_api()
        mongodb_client = test_mongodb_connection()
        repo = test_save_news(articles, mongodb_client)
        test_retrieve_news(repo)
        print("✓ 모든 테스트 완료")
    except Exception as e:
        print(f"✗ 테스트 실패: {e}")