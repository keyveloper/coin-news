"""TokenPost Page Crawler - Extract news links and dates from listing page"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TokenPostPageCrawler:
    """TokenPost cryptocurrency news listing page crawler"""

    BASE_URL = "https://www.tokenpost.kr/news/cryptocurrency"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_page(self, page: int = 1) -> str:
        """
        Fetch HTML content from TokenPost cryptocurrency news page

        Args:
            page: Page number (default 1)

        Returns:
            str: HTML content

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.BASE_URL}?page={page}"
        logger.info(f"Fetching TokenPost page: {url}")

        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()

        return response.text

    def parse_news_items(self, html_content: str) -> List[Dict]:
        """
        Parse news items from HTML content

        Args:
            html_content: HTML content

        Returns:
            List[Dict]: List of news items with link and datetime
                [
                    {
                        "link": "https://www.tokenpost.kr/article-123456",
                        "datetime": "2025.11.17 21:10",
                        "datetime_obj": datetime(2025, 11, 17, 21, 10)
                    },
                    ...
                ]
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        news_items = []

        # Find all article blocks
        list_left_item = soup.find('div', class_='list_left_item')
        if not list_left_item:
            logger.warning("list_left_item not found")
            return news_items

        articles = list_left_item.find_all('div', class_='list_left_item_article')
        logger.info(f"Found {len(articles)} articles")

        for article in articles:
            try:
                # Extract link from list_item_title
                title_div = article.find('div', class_='list_item_title')
                if not title_div:
                    continue

                a_tag = title_div.find('a')
                if not a_tag or not a_tag.get('href'):
                    continue

                link = a_tag.get('href')
                # Make absolute URL if relative
                if link.startswith('/'):
                    link = f"https://www.tokenpost.kr{link}"

                # Extract datetime from time tag
                write_div = article.find('div', class_='list_item_write')
                if not write_div:
                    continue

                time_tag = write_div.find('time', class_='day')
                if not time_tag or not time_tag.get('datetime'):
                    continue

                datetime_str = time_tag.get('datetime')

                # Parse datetime (format: "2025.11.17 21:10")
                try:
                    dt_obj = datetime.strptime(datetime_str, "%Y.%m.%d %H:%M")
                except ValueError:
                    logger.warning(f"Failed to parse datetime: {datetime_str}")
                    continue

                news_items.append({
                    "link": link,
                    "datetime": datetime_str,
                    "datetime_obj": dt_obj
                })

            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue

        logger.info(f"Successfully parsed {len(news_items)} news items")
        return news_items

    def collect_news_until_date(
        self,
        pivot_date: str,
        days_before: int = 30,
        max_pages: int = 50
    ) -> List[str]:
        """
        Collect news links from pivot_date to days_before

        Args:
            pivot_date: Reference date (YYYYMMDD format, e.g., "20251117")
            days_before: Number of days before pivot_date (default 30)
            max_pages: Maximum pages to crawl (default 50)

        Returns:
            List[str]: List of news URLs within date range
        """
        # Parse pivot_date
        try:
            pivot_dt = datetime.strptime(pivot_date, "%Y%m%d")
        except ValueError as e:
            logger.error(f"Invalid pivot_date format: {e}")
            raise

        # Calculate cutoff date (00:00 of days_before ago)
        cutoff_dt = pivot_dt - timedelta(days=days_before)
        cutoff_dt = cutoff_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        logger.info(f"Collecting news from {cutoff_dt} to {pivot_dt}")

        collected_links = []
        page = 1
        should_continue = True

        while should_continue and page <= max_pages:
            try:
                # Fetch page
                html_content = self.fetch_page(page)

                # Parse news items
                news_items = self.parse_news_items(html_content)

                if not news_items:
                    logger.warning(f"No news items found on page {page}")
                    break

                # Check each news item
                for item in news_items:
                    news_dt = item['datetime_obj']

                    # If news is older than cutoff, stop
                    if news_dt < cutoff_dt:
                        logger.info(f"Reached cutoff date at page {page}")
                        should_continue = False
                        break

                    # If news is within range, collect
                    if cutoff_dt <= news_dt <= pivot_dt:
                        collected_links.append(item['link'])

                logger.info(f"Page {page}: Collected {len([item for item in news_items if cutoff_dt <= item['datetime_obj'] <= pivot_dt])} links")
                page += 1

            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                break

        logger.info(f"Total collected: {len(collected_links)} news links")
        return collected_links


def main():
    """Test crawler"""
    crawler = TokenPostPageCrawler()

    # Test 1: Fetch single page
    print("\n" + "="*60)
    print("Test 1: Fetch page 1")
    print("="*60)
    html = crawler.fetch_page(1)
    print(f"HTML length: {len(html)} characters")

    # Test 2: Parse news items
    print("\n" + "="*60)
    print("Test 2: Parse news items from page 1")
    print("="*60)
    news_items = crawler.parse_news_items(html)
    for i, item in enumerate(news_items[:3], 1):
        print(f"{i}. {item['datetime']} - {item['link']}")

    # Test 3: Collect news for last 30 days
    print("\n" + "="*60)
    print("Test 3: Collect news from 2025-11-17 (30 days before)")
    print("="*60)
    links = crawler.collect_news_until_date(
        pivot_date="20251117",
        days_before=30,
        max_pages=5  # Limit for testing
    )
    print(f"Collected {len(links)} links")
    if links:
        print("First 3 links:")
        for link in links[:3]:
            print(f"  - {link}")


if __name__ == "__main__":
    main()
