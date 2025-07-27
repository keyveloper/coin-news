from abc import ABC, abstractmethod
import requests

class BaseCrawler:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_page(self, url: str) -> str:
        response = requests.get(url, headers=self.headers)
        return response.text

    @abstractmethod
    def crawl(self):
        """
        Crawl each webpage - Analyze HTML structure
        :return:
        """
        return

