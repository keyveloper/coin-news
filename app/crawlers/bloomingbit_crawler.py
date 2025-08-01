from app.crawlers.base_crawler import BaseCrawler
from urllib.parse import urljoin


class BloomingbitCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("https://bloomingbit.io/")

    def get_soup(self):
        """HTML 가져와서 BeautifulSoup 객체 반환"""
        html = self.fetch_html()
        return self.to_soup(html)

    def get_ranking_news_urls(self):
        """
        rankingNewsSwiper에서 랭킹 뉴스 URL과 제목 추출
        Returns: [{'title': str, 'href': str}, ...]
        """
        try:
            soup = self.get_soup()
            ranking_news = []

            # rankingNewsSwiper 클래스 찾기
            swiper = soup.find('div', class_=lambda x: x and 'rankingNewsSwiper' in x)

            if not swiper:
                print("rankingNewsSwiper를 찾을 수 없습니다.")
                return []

            # swiper 내부의 모든 a 태그 찾기
            news_links = swiper.find_all('a', href=True)

            print(f"발견된 랭킹 뉴스 링크: {len(news_links)}개")

            for link in news_links:
                href = link.get('href')
                if not href:
                    continue

                # 절대 URL로 변환
                full_url = urljoin(self.base_url, href)

                # 제목 찾기 (h3 태그의 title 클래스)
                title_tag = link.find('h3', class_='title')
                title = title_tag.get_text(strip=True) if title_tag else '제목 없음'

                # 랭킹 번호 찾기 (선택사항)
                rank_tag = link.find('span', class_='rankingNewsLabelNumber')
                rank = rank_tag.get_text(strip=True) if rank_tag else None

                news_item = {
                    'title': title,
                    'href': full_url,
                    'rank': rank
                }

                ranking_news.append(news_item)

            print(f"추출 완료: {len(ranking_news)}개 랭킹 뉴스")
            return ranking_news

        except Exception as e:
            print(f"랭킹 뉴스 추출 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            self.close_selenium()

    def extract_news_urls(self):
        pass

    def get_news_list(self):
        pass
