from app.crawlers.base_crawler import BaseCrawler

class CoinNewsCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("https://coinnews.com/")

    def crawl(self):
        """
        Placeholder - crawl logic will be implemented later
        """
        pass

