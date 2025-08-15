from bs4 import BeautifulSoup
from typing import Dict, Optional


def parse_tokenpost_news(html_content: str, url: str) -> Dict:
    """
    TokenPost 뉴스 메타데이터 추출

    Args:
        html_content: HTML XP 
        url: t� URL

    Returns:
        Dict: �� T�pt0
            - url: t� URL
            - title: t� �
            - published_date: � ��
            - reporter_name: 0� t�
            - article_content: �8 ��
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    result_data = {
        "url": url,
        "title": None,
        "published_date": None,
        "reporter_name": None,
        "article_content": None
    }

    # 1. t� � (<title> ��)
    if soup.title:
        result_data['title'] = soup.title.string

    # 2. � �� (<time> ��)
    time_tag = soup.find('time')
    if time_tag:
        result_data['published_date'] = time_tag.get_text(strip=True)

    # 3. 기자 이름
    # 방법 1: class="view_title_bottom_name"
    reporter_name = soup.find(class_='view_title_bottom_name')
    if reporter_name:
        result_data['reporter_name'] = reporter_name.get_text(strip=True)
    else:
        # 방법 2: class="contributor_item_text"의 a > span
        contributor_item = soup.find(class_='contributor_item_text')
        if contributor_item:
            a_tag = contributor_item.find('a')
            if a_tag:
                span_tag = a_tag.find('span')
                if span_tag:
                    result_data['reporter_name'] = span_tag.get_text(strip=True)

    # 4. �8 �� (class="article_content")
    article_content = soup.find('div', class_='article_content')
    if article_content:
        result_data['article_content'] = article_content.get_text(strip=True)

    return result_data


def is_tokenpost_url(url: str) -> bool:
    """
    TokenPost URLx� Ux

    Args:
        url: Ux` URL

    Returns:
        bool: TokenPost URL �
    """
    return 'tokenpost' in url.lower()