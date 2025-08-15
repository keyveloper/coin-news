from fastapi import APIRouter, Query, HTTPException
import requests
from bs4 import BeautifulSoup

from app.schemas.test import MyCustomResponse, MyCustomRequest
from app.services.naver_news_search_service import NaverNewsSearchService
from app.parser.coinreaders_parser import parse_coinreaders_news
from app.parser.digitaltoday_parser import parse_digitaltoday_news
from app.parser.tokenpost_parser import parse_tokenpost_news

test_router = APIRouter(prefix="/test", tags=["test"])


@test_router.get("", response_model=MyCustomResponse)
def get_test(name: str = Query(
    ..., #required parameter
    min_length=2,
    max_length=10,
)):
    return MyCustomResponse(message=f"{name} successful")


@test_router.get("/body", response_model=MyCustomResponse)
def read_body(request: MyCustomRequest):
    return MyCustomResponse(message=f"hello!! {request.name}, {request.age}")

@test_router.get("/soup", response_model=dict)
def get_soup(url: str = Query(..., description="분석할 뉴스 사이트 URL")):
    """
    URL의 HTML Raw 데이터 조회

    Args:
        url: 분석할 뉴스 사이트 URL

    Returns:
        기본 정보와 HTML raw 데이터
    """
    try:
        # HTTP 요청
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(response.content, 'html.parser')

        # 기본 정보
        basic_info = {
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get('Content-Type'),
            "title": soup.title.string if soup.title else None,
            "paragraphs_count": len(soup.find_all('p')),
            "images_count": len(soup.find_all('img')),
            "links_count": len(soup.find_all('a'))
        }

        # Raw HTML (prettified)
        html_raw = soup.prettify()

        return {
            "status": "success",
            "message": "HTML 데이터 조회 완료",
            "data": {
                "basic_info": basic_info,
                "html_raw": html_raw
            }
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"URL 요청 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HTML 파싱 오류: {str(e)}")


@test_router.get("/news-distribution", response_model=dict)
def analyze_news_distribution(
    query: str = Query(..., description="검색어"),
    iterations: int = Query(description="반복 횟수"),
    display: int = Query(default=100, description="한 번에 가져올 뉴스 개수")
):
    """
    뉴스 사이트 분포도 분석

    Args:
        query: 검색어
        iterations: 반복 횟수 (1~20)
        display: 한 번에 가져올 뉴스 개수 (1~100)

    Returns:
        뉴스 사이트별 분포 통계
    """
    try:
        service = NaverNewsSearchService()
        return service.analyze_news_site_distribution(
            query=query,
            iterations=iterations,
            display=display
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@test_router.get("/parse-coinreaders", response_model=dict)
def parse_coinreaders(url: str = Query(..., description="CoinReaders 뉴스 URL")):
    """
    CoinReaders 뉴스 메타데이터 추출 테스트

    Args:
        url: CoinReaders 뉴스 URL

    Returns:
        추출된 뉴스 메타데이터 (제목, 기자, 날짜, 본문)
    """
    try:
        # HTTP 요청
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # CoinReaders 파서 실행
        result_data = parse_coinreaders_news(response.text, url)

        return {
            "status": "success",
            "message": "CoinReaders 뉴스 데이터 추출 완료",
            "data": result_data
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"URL 요청 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파싱 오류: {str(e)}")


@test_router.get("/parse-digitaltoday", response_model=dict)
def parse_digitaltoday(url: str = Query(..., description="DigitalToday 뉴스 URL")):
    """
    DigitalToday 뉴스 메타데이터 추출 테스트

    Args:
        url: DigitalToday 뉴스 URL

    Returns:
        추출된 뉴스 메타데이터 (제목, 기자, 날짜, 본문)
    """
    try:
        # HTTP 요청
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # DigitalToday 파서 실행
        result_data = parse_digitaltoday_news(response.text, url)

        return {
            "status": "success",
            "message": "DigitalToday 뉴스 데이터 추출 완료",
            "data": result_data
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"URL 요청 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파싱 오류: {str(e)}")


@test_router.get("/parse-tokenpost", response_model=dict)
def parse_tokenpost(url: str = Query(..., description="TokenPost 뉴스 URL")):
    """
    TokenPost 뉴스 메타데이터 추출 테스트

    Args:
        url: TokenPost 뉴스 URL

    Returns:
        추출된 뉴스 메타데이터 (제목, 기자, 날짜, 본문)
    """
    try:
        # HTTP 요청
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # TokenPost 파서 실행
        result_data = parse_tokenpost_news(response.text, url)

        return {
            "status": "success",
            "message": "TokenPost 뉴스 데이터 추출 완료",
            "data": result_data
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"URL 요청 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파싱 오류: {str(e)}")