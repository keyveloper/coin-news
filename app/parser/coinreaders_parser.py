from bs4 import BeautifulSoup
from typing import Dict, Optional
import re
import requests
from app.schemas.parser import CoinReaderMetadata, CoinReaderMetadatWithRaw


def parse_coinreaders_news(url: str) -> CoinReaderMetadatWithRaw:
    # URL에서 HTML 가져오기
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    html_content = response.text

    soup = BeautifulSoup(html_content, 'html.parser')

    title = ""
    authors = ""
    published_date = ""
    description = ""
    page_content = ""

    # 1. 뉴스 제목 (<h1 class="read_title">)
    title_tag = soup.find('h1', class_='read_title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        description = title  # description을 title과 동일하게 설정

    # 3. 기자 이름 및 날짜 (<div class="writer_time">)
    writer_time_div = soup.find('div', class_='writer_time')
    if writer_time_div:
        # 기자 이름 (<span class="writer">)
        writer_span = writer_time_div.find('span', class_='writer')
        if writer_span:
            authors = writer_span.get_text(strip=True)

        # 날짜 추출 (텍스트에서 "기사입력  2025/11/10 [10:21]" 형식 찾기)
        text = writer_time_div.get_text()
        # 정규식으로 날짜 패턴 추출: YYYY/MM/DD [HH:MM]
        date_pattern = r'기사입력\s+(\d{4}/\d{2}/\d{2}\s+\[\d{2}:\d{2}\])'
        date_match = re.search(date_pattern, text)
        if date_match:
            published_date = date_match.group(1).strip()

    # 4. 본문 내용 (<div id="textinput">의 <p> 태그들)
    textinput_div = soup.find('div', id='textinput')
    if textinput_div:
        # 모든 p 태그 추출
        paragraphs = textinput_div.find_all('p')
        if paragraphs:
            # p 태그들의 텍스트를 합침
            article_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            page_content = article_text
        else:
            # p 태그가 없으면 전체 텍스트 추출
            page_content = textinput_div.get_text(strip=True)

    metadata = CoinReaderMetadata(
        title=title,
        link=url,
        authors=authors,
        language="ko",
        description=description,
        published_date=published_date
    )

    return CoinReaderMetadatWithRaw(
        page_content=page_content,
        metadata=metadata
    )


