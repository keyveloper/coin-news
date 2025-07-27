import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from app.crawlers.coinnews_crawler import CoinNewsCrawler
from pathlib import Path

load_dotenv()


def coin_news_scrape():
    """
    Scrape coin news using BeautifulSoup
    CoinNewsCrawler는 base_url만 제공
    """
    # Step 1: Get base URL from CoinNewsCrawler
    crawler = CoinNewsCrawler()
    url = crawler.base_url
    user_agent = crawler.headers.get("User-Agent")

    print(f"[Step 1] Fetching URL: {url}")
    response = requests.get(url, headers={
        'User-Agent': user_agent
    })

    print(f"[Step 2] Status Code: {response.status_code}")

    # 프로젝트 루트 디렉토리 찾기 (app/services -> 상위 2단계)
    # scraper.py의 위치: coin-news/app/services/scraper.py
    # 루트 디렉토리: coin-news/
    current_file = Path(__file__)  # scraper.py 파일 경로
    project_root = current_file.parent.parent.parent  # coin-news/
    test_dir = project_root / "test"  # coin-news/test/

    # test 디렉토리가 없으면 생성
    test_dir.mkdir(exist_ok=True)

    print(f"[Step 3] Saving files to: {test_dir}")

    # 1. response 객체 정보 저장
    response_file = test_dir / "response.txt"
    with open(response_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Response Object Information\n")
        f.write("=" * 80 + "\n")
        f.write(f"URL: {response.url}\n")
        f.write(f"Status Code: {response.status_code}\n")
        f.write(f"Headers: {response.headers}\n")
        f.write(f"Encoding: {response.encoding}\n")
        f.write(f"Content Length: {len(response.content)} bytes\n")
    print(f"✅ Saved: {response_file}")

    # 2. response.text (raw HTML) 저장
    response_text_file = test_dir / "response_text.txt"
    with open(response_text_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"✅ Saved: {response_text_file}")

    # 3. soup (parsed HTML) 저장
    soup = BeautifulSoup(response.text, "lxml")
    soup_file = test_dir / "soup.txt"
    with open(soup_file, 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print(f"✅ Saved: {soup_file}")

    print(f"\n[Complete] All files saved to: {test_dir.absolute()}")

    return soup
