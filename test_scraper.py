"""
BeautifulSoup 크롤링 테스트 스크립트
"""
from app.services.scraper import coin_news_scrape


def main():
    print("=" * 60)
    print("BeautifulSoup 크롤링 테스트 시작")
    print("=" * 60)

    # 크롤링 실행
    articles = coin_news_scrape()

    # 결과 출력
    print("\n" + "=" * 60)
    print("크롤링 결과")
    print("=" * 60)

    if articles:
        for idx, article in enumerate(articles, 1):
            print(f"\n[Article {idx}]")
            print(f"Title: {article['title']}")
            print(f"URL: {article['url']}")
            print(f"Source: {article['source']}")
    else:
        print("크롤링된 기사가 없습니다.")

    print("\n" + "=" * 60)
    print(f"총 {len(articles)}개 기사 수집 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()