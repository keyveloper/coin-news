"""
HTML 구조 분석 디버깅 스크립트
"""
import requests
from bs4 import BeautifulSoup
from app.crawlers.coinnews_crawler import CoinNewsCrawler


def debug_html_structure():
    """HTML 구조여를 출력하 분석"""
    crawler = CoinNewsCrawler()
    base_url = crawler.base_url

    print(f"Fetching: {base_url}\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = requests.get(base_url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')

    print("=" * 80)
    print("HTML 구조 분석")
    print("=" * 80)

    # 1. 모든 h1, h2, h3 태그 찾기
    print("\n[1] 제목 태그 (h1, h2, h3):")
    for tag_name in ['h1', 'h2', 'h3']:
        tags = soup.find_all(tag_name, limit=3)
        if tags:
            print(f"\n  {tag_name.upper()} 태그 ({len(soup.find_all(tag_name))}개 발견):")
            for i, tag in enumerate(tags, 1):
                print(f"    {i}. {tag.get_text(strip=True)[:60]}...")
                print(f"       클래스: {tag.get('class', 'None')}")

    # 2. article 태그 찾기
    print("\n[2] Article 태그:")
    articles = soup.find_all('article', limit=3)
    if articles:
        print(f"  총 {len(soup.find_all('article'))}개 발견")
        for i, article in enumerate(articles, 1):
            print(f"\n  Article {i}:")
            print(f"    클래스: {article.get('class', 'None')}")
            title = article.find(['h1', 'h2', 'h3', 'h4'])
            if title:
                print(f"    제목: {title.get_text(strip=True)[:60]}...")
    else:
        print("  Article 태그 없음")

    # 3. 링크 태그 찾기 (a 태그)
    print("\n[3] 링크 태그 (a):")
    links = soup.find_all('a', href=True, limit=5)
    for i, link in enumerate(links, 1):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if text:  # 텍스트가 있는 링크만
            print(f"  {i}. {text[:60]}...")
            print(f"     URL: {href[:80]}")

    # 4. HTML 일부 출력
    print("\n[4] HTML 본문 샘플 (처음 500자):")
    print("-" * 80)
    print(soup.prettify()[:500])
    print("-" * 80)

    # 5. 저장 옵션
    save = input("\n전체 HTML을 파일로 저장하시겠습니까? (y/n): ").lower()
    if save == 'y':
        with open('html_debug_output.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("✅ 'html_debug_output.html' 파일로 저장되었습니다.")


if __name__ == "__main__":
    debug_html_structure()