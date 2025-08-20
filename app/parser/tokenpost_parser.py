from bs4 import BeautifulSoup
from typing import Dict, Optional
from app.schemas.metadata import GeneralMetadata, GeneralMetadatWithRaw


def parse_tokenpost_news(html_content: str, url: str) -> GeneralMetadatWithRaw:
    """
    TokenPost 뉴스 메타데이터 추출

    Args:
        html_content: HTML 콘텐츠
        url: 뉴스 URL

    Returns:
        GeneralMetadatWithRaw: 뉴스 메타데이터와 본문
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    title = ""
    authors = ""
    published_date = ""
    description = ""
    page_content = ""

    # 1. 뉴스 제목 (<title> 태그)
    if soup.title:
        title = soup.title.string
        description = title  # description을 title과 동일하게 설정

    # 2. 게시 날짜 (<time> 태그)
    time_tag = soup.find('time')
    if time_tag:
        published_date = time_tag.get_text(strip=True)

    # 3. 기자 이름
    # 방법 1: class="view_title_bottom_name"
    reporter_name = soup.find(class_='view_title_bottom_name')
    if reporter_name:
        authors = reporter_name.get_text(strip=True)
    else:
        # 방법 2: class="contributor_item_text"의 a > span
        contributor_item = soup.find(class_='contributor_item_text')
        if contributor_item:
            a_tag = contributor_item.find('a')
            if a_tag:
                span_tag = a_tag.find('span')
                if span_tag:
                    authors = span_tag.get_text(strip=True)

    # 4. 기사 본문 (class="article_content")
    article_content = soup.find('div', class_='article_content')
    if article_content:
        page_content = article_content.get_text(strip=True)

    metadata = GeneralMetadata(
        title=title,
        link=url,
        authors=authors,
        language="ko",
        description=description,
        published_date=published_date
    )

    return GeneralMetadatWithRaw(
        page_content=page_content,
        metadata=metadata
    )


def is_tokenpost_url(url: str) -> bool:
    """
    TokenPost URL인지 확인

    Args:
        url: 확인할 URL

    Returns:
        bool: TokenPost URL 여부
    """
    return 'tokenpost' in url.lower()
