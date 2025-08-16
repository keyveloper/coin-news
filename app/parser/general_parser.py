"""General 뉴스 파서 - WebBaseLoader 사용"""
from langchain_community.document_loaders import WebBaseLoader
from typing import Dict


def parse_general_news(url: str) -> Dict:
    """
    WebBaseLoader를 사용하여 뉴스 메타데이터 추출

    Args:
        url: 뉴스 URL

    Returns:
        Dict: 추출된 메타데이터
            - url: 뉴스 URL
l            - title: 뉴스 제목
            - published_date: 발행 날짜 (기본 None)
            - reporter_name: 기자 이름 (기본 None)
            - article_content: 본문 내용 (줄바꿈 제거됨)
            - source: 페이지 소스 URL
            - description: 메타 description
            - language: 페이지 언어
            - og_title, og_description, og_image, og_url, og_type, og_site_name: Open Graph 메타데이터
            - twitter_card, twitter_title, twitter_description, twitter_image: Twitter Card 메타데이터
            - author: 작성자
            - keywords: 키워드
            - metadata_raw: WebBaseLoader가 추출한 원본 메타데이터 전체
    """
    # WebBaseLoader로 페이지 로드


    loader = WebBaseLoader(web_paths=[url])
    docs = loader.load()

    # 첫 번째 문서 사용
    if docs and len(docs) > 0:
        doc = docs[0]

        # article_content 전처리: \n 제거
        article_content = None
        if doc.page_content:
            article_content = doc.page_content.replace('\n', ' ').strip()

        # WebBaseLoader가 추출하는 주요 메타데이터 매핑
        result_data = {
            "url": url,
            "title": doc.metadata.get('title'),
            "published_date": None,  # WebBaseLoader는 기본적으로 발행 날짜를 추출하지 않음
            "reporter_name": None,   # WebBaseLoader는 기본적으로 기자 이름을 추출하지 않음
            "article_content": article_content,

            # WebBaseLoader가 추출한 메타데이터들
            "source": doc.metadata.get('source'),  # URL
            "description": doc.metadata.get('description'),  # meta description
            "language": doc.metadata.get('language'),  # 페이지 언어

            # Open Graph 메타데이터 (있는 경우)
            "og_title": doc.metadata.get('og:title'),
            "og_description": doc.metadata.get('og:description'),
            "og_image": doc.metadata.get('og:image'),
            "og_url": doc.metadata.get('og:url'),
            "og_type": doc.metadata.get('og:type'),
            "og_site_name": doc.metadata.get('og:site_name'),

            # Twitter Card 메타데이터 (있는 경우)
            "twitter_card": doc.metadata.get('twitter:card'),
            "twitter_title": doc.metadata.get('twitter:title'),
            "twitter_description": doc.metadata.get('twitter:description'),
            "twitter_image": doc.metadata.get('twitter:image'),

            # 기타 메타데이터
            "author": doc.metadata.get('author'),
            "keywords": doc.metadata.get('keywords'),

            # 원본 메타데이터 전체 (참고용)
            "metadata_raw": doc.metadata
        }

        return result_data
    else:
        # 문서를 찾지 못한 경우
        return {
            "url": url,
            "title": None,
            "published_date": None,
            "reporter_name": None,
            "article_content": None,
            "source": None,
            "description": None,
            "language": None,
            "og_title": None,
            "og_description": None,
            "og_image": None,
            "og_url": None,
            "og_type": None,
            "og_site_name": None,
            "twitter_card": None,
            "twitter_title": None,
            "twitter_description": None,
            "twitter_image": None,
            "author": None,
            "keywords": None,
            "metadata_raw": {}
        }