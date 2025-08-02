from app.crawlers.base_crawler import BaseCrawler
from urllib.parse import urljoin


class BloomingbitCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("https://bloomingbit.io/")

    def get_soup(self, url: str = None, wait_time: int = 8):
        """
        HTML 가져와서 BeautifulSoup 객체 반환
        Args:
            url: 크롤링할 URL (None이면 base_url 사용)
            wait_time: 페이지 로딩 대기 시간 (초)
        Returns:
            BeautifulSoup 객체
        """
        html = self.fetch_html(url=url, wait_time=wait_time)
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

    def extract_article_metadata(self, url: str):
        """
        기사 URL에서 메타데이터 추출
        Args:
            url: 기사 URL (예: https://bloomingbit.io/feed/news/99546)
        Returns:
            메타데이터 딕셔너리
        """
        try:
            soup = self.get_soup(url=url)
            metadata = {}

            # URL 파싱
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            url_parts = parsed_url.path.strip('/').split('/')

            # === 기본 정보 ===
            # title
            title_tag = soup.find('title')
            metadata['title'] = title_tag.get_text(strip=True) if title_tag else None

            # og_title
            og_title_tag = soup.find('meta', property='og:title')
            metadata['og_title'] = og_title_tag['content'] if og_title_tag and og_title_tag.get('content') else None

            # description
            desc_tag = soup.find('meta', {'name': 'description'})
            metadata['description'] = desc_tag['content'] if desc_tag and desc_tag.get('content') else None

            # og_description
            og_desc_tag = soup.find('meta', property='og:description')
            metadata['og_description'] = og_desc_tag['content'] if og_desc_tag and og_desc_tag.get('content') else None

            # keywords
            keywords_tag = soup.find('meta', {'name': 'keywords'})
            if keywords_tag and keywords_tag.get('content'):
                metadata['keywords'] = [k.strip() for k in keywords_tag['content'].split(',')]
            else:
                metadata['keywords'] = []

            # language
            html_tag = soup.find('html')
            metadata['language'] = html_tag.get('lang') if html_tag and html_tag.get('lang') else None

            # === URL 관련 ===
            # canonical_url
            canonical_tag = soup.find('link', rel='canonical')
            canonical_url = canonical_tag['href'] if canonical_tag and canonical_tag.get('href') else url
            metadata['canonical_url'] = canonical_url

            # source_domain
            metadata['source_domain'] = urlparse(canonical_url).netloc

            # article_id
            metadata['article_id'] = url_parts[-1] if len(url_parts) > 0 else None

            # category
            metadata['category'] = url_parts[-2] if len(url_parts) > 1 else None

            # === Open Graph ===
            # og_image
            og_image_tag = soup.find('meta', property='og:image')
            metadata['og_image'] = og_image_tag['content'] if og_image_tag and og_image_tag.get('content') else None

            # og_url
            og_url_tag = soup.find('meta', property='og:url')
            metadata['og_url'] = og_url_tag['content'] if og_url_tag and og_url_tag.get('content') else None

            # og_type
            og_type_tag = soup.find('meta', property='og:type')
            metadata['og_type'] = og_type_tag['content'] if og_type_tag and og_type_tag.get('content') else None

            # === 기타 메타 ===
            # fb_app_id
            fb_app_id_tag = soup.find('meta', {'name': 'fb:app_id'})
            metadata['fb_app_id'] = fb_app_id_tag['content'] if fb_app_id_tag and fb_app_id_tag.get('content') else None

            # robots
            robots_tag = soup.find('meta', {'name': 'robots'})
            metadata['robots'] = robots_tag['content'] if robots_tag and robots_tag.get('content') else None

            # theme_color
            theme_color_tag = soup.find('meta', {'name': 'theme-color'})
            metadata['theme_color'] = theme_color_tag['content'] if theme_color_tag and theme_color_tag.get('content') else None

            # === Footer 정보 ===
            footer = soup.find('footer')
            if footer:
                # source_name
                source_span = footer.find('span')
                metadata['source_name'] = source_span.get_text(strip=True) if source_span else None

                # publisher (발행·편집인)
                publisher_span = footer.find('span', string=lambda x: x and '발행·편집인' in x)
                metadata['publisher'] = publisher_span.get_text(strip=True) if publisher_span else None

                # company_address
                address_span = footer.find('span', string=lambda x: x and '서울시' in x)
                metadata['company_address'] = address_span.get_text(strip=True) if address_span else None

                # business_number
                business_span = footer.find('span', string=lambda x: x and '사업자' in x)
                metadata['business_number'] = business_span.get_text(strip=True) if business_span else None
            else:
                metadata['source_name'] = None
                metadata['publisher'] = None
                metadata['company_address'] = None
                metadata['business_number'] = None

            # === 본문 콘텐츠 ===
            # content
            article_tag = soup.find('article')
            metadata['content'] = article_tag.get_text(strip=True) if article_tag else None

            # === 다국어 지원 ===
            # alternate_languages
            alternate_links = soup.find_all('link', rel='alternate', hreflang=True)
            metadata['alternate_languages'] = [link.get('hreflang') for link in alternate_links]

            # === 동적 데이터 (추출 불가) ===
            metadata['published_date'] = None  # 본문 파싱 필요
            metadata['author'] = None  # 본문 파싱 필요
            metadata['view_count'] = None  # JavaScript 동적 로드
            metadata['comment_count'] = None  # JavaScript 동적 로드

            print(f"✅ 메타데이터 추출 완료: {metadata.get('title', 'Unknown')}")
            return metadata

        except Exception as e:
            print(f"❌ 메타데이터 추출 실패: {e}")
            import traceback
            traceback.print_exc()
            return {}
        finally:
            self.close_selenium()


    def get_news_list(self):
        pass
