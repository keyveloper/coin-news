from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

class BaseCrawler:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.driver = None

    def init_selenium(self):
        """Initialize Selenium WebDriver"""
        if self.driver:
            return

        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

        try:
            driver_path = ChromeDriverManager().install()

            if "THIRD_PARTY_NOTICES.chromedriver" in driver_path:
                driver_path = driver_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver.exe")

            print(f"ChromeDriver 경로: {driver_path}")
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("Selenium 초기화 완료")
        except Exception as e:
            print(f"Selenium 초기화 오류: {e}")
            raise

    def close_selenium(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("Selenium 종료 완료")

    def fetch_html(self, url: str = None, wait_time: int = 8) -> str:
        """
        Selenium으로 페이지를 가져와서 HTML 문자열 반환
        """
        target_url = url or self.base_url
        print(f"Selenium으로 페이지 요청 중: {target_url}")

        self.init_selenium()
        self.driver.get(target_url)

        print(f"{wait_time}초 동안 페이지 로딩 대기 중...")
        time.sleep(wait_time)

        html = self.driver.page_source
        print(f"페이지 로딩 완료 (HTML 크기: {len(html)} bytes)")

        return html

    def to_soup(self, html: str) -> BeautifulSoup:
        """
        HTML 문자열을 BeautifulSoup 객체로 변환
        """
        soup = BeautifulSoup(html, 'html.parser')
        return soup

