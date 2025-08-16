"""News URL Loader 파서 - LangChain NewsURLLoader 사용"""
from langchain_community.document_loaders import NewsURLLoader
from typing import Dict
from datetime import datetime


def parse_news_with_urlloader(url: str) -> Dict:
    """
    LangChain NewsURLLoader를 사용하여 뉴스 메타데이터 추출

    Args:
        url: 뉴스 URL

    Returns:
        Dict: documents[0]의 page_content와 metadata를 그대로 반환
    """
    try:
        # NewsURLLoader로 페이지 로드
        loader = NewsURLLoader(urls=[url])
        documents = loader.load()

        # documents가 비어있지 않은 경우
        if documents:
            doc = documents[0]

            # 발행 날짜를 문자열로 변환 (datetime 객체인 경우)
            publish_date = doc.metadata.get('publish_date')
            if publish_date and hasattr(publish_date, 'isoformat'):
                doc.metadata['publish_date'] = publish_date.isoformat()

            # 저자 리스트를 문자열로 변환
            authors = doc.metadata.get('authors')
            if isinstance(authors, list):
                doc.metadata['authors_string'] = ", ".join(authors) if authors else None

            # 결과 반환 (단순화)
            return {
                "url": url,
                "article_content": doc.page_content,
                "content_length": len(doc.page_content) if doc.page_content else 0,
                "extracted_at": datetime.now().isoformat(),
                **doc.metadata  # metadata를 그대로 펼쳐서 반환
            }

        # documents가 비어있는 경우
        return {
            "url": url,
            "article_content": None,
            "error": "문서를 로드할 수 없습니다"
        }

    except Exception as e:
        return {
            "url": url,
            "article_content": None,
            "error": f"파싱 중 오류 발생: {str(e)}"
        }