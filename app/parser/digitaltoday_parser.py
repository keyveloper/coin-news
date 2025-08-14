"""DigitalToday 뉴스 파서"""
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re


def parse_digitaltoday_news(html_content: str, url: str) -> Dict:
    """
    DigitalToday 뉴스 메타데이터 추출

    Args:
        html_content: HTML 콘텐츠
        url: 뉴스 URL

    Returns:
        Dict: 추출된 메타데이터
            - url: 뉴스 URL
            - title: 뉴스 제목
            - published_date: 발행 날짜
            - reporter_name: 기자 이름
            - article_content: 본문 내용
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    result_data = {
        "url": url,
        "title": None,
        "published_date": None,
        "reporter_name": None,
        "article_content": None
    }

    # 1. 뉴스 제목 (<h3 class="heading">)
    title_tag = soup.find('h3', class_='heading')
    if title_tag:
        result_data['title'] = title_tag.get_text(strip=True)

    # 2. 기자 이름 및 날짜 (<ul class="infomation">)
    info_ul = soup.find('ul', class_='infomation')
    if info_ul:
        li_tags = info_ul.find_all('li')

        for li in li_tags:
            text = li.get_text(strip=True)

            # 기자 이름 추출 (예: "이호정 기자", "기자명이호정 기자" 등)
            if '기자' in text:
                # "기자명" 텍스트 제거 후 기자 이름 추출
                reporter_text = text.replace('기자명', '').strip()
                if reporter_text:
                    result_data['reporter_name'] = reporter_text

            # 날짜 추출 (예: "입력 2025.11.10 16:32")
            elif '입력' in text:
                # "입력" 텍스트 제거 후 날짜 추출
                date_text = text.replace('입력', '').strip()
                if date_text:
                    result_data['published_date'] = date_text

    # 3. 본문 내용 (<article id="article-view-content-div"> 내의 <p> 태그들)
    article_tag = soup.find('article', id='article-view-content-div')
    if article_tag:
        # 모든 p 태그 추출
        paragraphs = article_tag.find_all('p')
        if paragraphs:
            # p 태그들의 텍스트를 합침 (광고 등 제외하고 실제 본문만)
            article_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            result_data['article_content'] = article_text
        else:
            # p 태그가 없으면 전체 텍스트 추출
            result_data['article_content'] = article_tag.get_text(strip=True)

    return result_data


def is_digitaltoday_url(url: str) -> bool:
    """
    DigitalToday URL인지 확인

    Args:
        url: 확인할 URL

    Returns:
        bool: DigitalToday URL 여부
    """
    return 'digitaltoday' in url.lower()