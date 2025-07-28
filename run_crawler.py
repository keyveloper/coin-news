"""
크롤러 실행 스크립트
CoinNewsCrawler를 실행하여 https://coinness.com/ 에 접속하고 데이터를 수집합니다.
"""

from app.crawlers.coinnews_crawler import CoinNewsCrawler

def main():
    # CoinNewsCrawler 인스턴스 생성
    crawler = CoinNewsCrawler()

    try:
        # 크롤링 실행
        soup = crawler.crawl()

        # 크롤링 결과를 HTML 파일로 저장 (선택사항)
        with open('coinness_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("\n페이지 HTML이 'coinness_page.html'에 저장되었습니다.")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()