"""CoinReaders 뉴스 파서"""
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re


def parse_coinreaders_news(html_content: str, url: str) -> Dict:
    """
    CoinReaders 뉴스 메타데이터 추출

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

    # 1. 뉴스 제목 (<h1 class="read_title">)
    title_tag = soup.find('h1', class_='read_title')
    if title_tag:
        result_data['title'] = title_tag.get_text(strip=True)

    # 3. 기자 이름 및 날짜 (<div class="writer_time">)
    writer_time_div = soup.find('div', class_='writer_time')
    if writer_time_div:
        # 기자 이름 (<span class="writer">)
        writer_span = writer_time_div.find('span', class_='writer')
        if writer_span:
            result_data['reporter_name'] = writer_span.get_text(strip=True)

        # 날짜 추출 (텍스트에서 "기사입력  2025/11/10 [10:21]" 형식 찾기)
        text = writer_time_div.get_text()
        # 정규식으로 날짜 패턴 추출: YYYY/MM/DD [HH:MM]
        date_pattern = r'기사입력\s+(\d{4}/\d{2}/\d{2}\s+\[\d{2}:\d{2}\])'
        date_match = re.search(date_pattern, text)
        if date_match:
            result_data['published_date'] = date_match.group(1).strip()

    # 4. 본문 내용 (<div id="textinput">의 <p> 태그들)
    textinput_div = soup.find('div', id='textinput')
    if textinput_div:
        # 모든 p 태그 추출
        paragraphs = textinput_div.find_all('p')
        if paragraphs:
            # p 태그들의 텍스트를 합침
            article_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            result_data['article_content'] = article_text
        else:
            # p 태그가 없으면 전체 텍스트 추출
            result_data['article_content'] = textinput_div.get_text(strip=True)

    return result_data


def is_coinreaders_url(url: str) -> bool:
    """
    CoinReaders URL인지 확인

    Args:
        url: 확인할 URL

    Returns:
        bool: CoinReaders URL 여부
    """
    return 'coinreaders' in url.lower()
