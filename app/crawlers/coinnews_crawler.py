from app.crawlers.base_crawler import BaseCrawler
from urllib.parse import urljoin

class CoinNewsCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("https://coinness.com/news")

    def extract_news_urls(self, soup):
        """
        뉴스 기사 URL과 제목 추출
        Returns: [{'title': str, 'url': str}, ...]
        """
        news_data = []

        # BreakingNewsTitle 클래스로 뉴스 제목 찾기
        news_titles = soup.find_all('div', class_=lambda x: x and 'BreakingNewsTitle' in x)

        print(f"'{len(news_titles)}개의 뉴스 제목 발견")

        seen_urls = set()
        for title_div in news_titles:
            # a 태그 찾기
            link = title_div.find('a', href=True)
            if not link:
                continue

            href = link.get('href')
            if not href:
                continue

            # 상대 URL을 절대 URL로 변환
            full_url = urljoin(self.base_url, href)

            # 중복 제거
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # 제목 텍스트 추출
            title = link.get_text(strip=True)

            news_item = {
                'title': title if title else '제목 없음',
                'url': full_url
            }
            news_data.append(news_item)

        print(f"crawling result: ${news_data}")

        return news_data

    def crawl(self):
        """
        1. Selenium으로 HTML 가져오기
        2. BeautifulSoup 객체로 변환
        3. extract_news_urls 호출하여 뉴스 데이터 추출
        4. 결과 반환
        """
        try:
            print("=" * 50)
            print("CoinNewsCrawler 시작")
            print(f"대상 URL: {self.base_url}")
            print("=" * 50)

            # 1. fetch_html로 HTML 가져오기
            html = self.fetch_html()
            print(f"\nHTML 가져오기 완료 (크기: {len(html)} bytes)")

            # 2. to_soup로 변환
            soup = self.to_soup(html)
            print(f"BeautifulSoup 변환 완료")

            # 페이지 제목 출력
            title = soup.find('title')
            if title:
                print(f"페이지 제목: {title.get_text()}")

            # 3. extract_news_urls 호출
            news_data = self.extract_news_urls(soup)
            print(f"\n추출된 뉴스 개수: {len(news_data)}개")

            print("=" * 50)
            print("크롤링 완료")
            print("=" * 50)

            # 4. 뉴스 데이터 반환
            return news_data

        finally:
            # Selenium 종료
            self.close_selenium()