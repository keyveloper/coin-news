from fastapi import APIRouter, Query, HTTPException
import requests
from bs4 import BeautifulSoup

from app.schemas.test import MyCustomResponse, MyCustomRequest
from app.services.naver_news_search_service import NaverNewsSearchService
from app.parser.coinreaders_parser import parse_coinreaders_news
from app.parser.digitaltoday_parser import parse_digitaltoday_news

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
    URL의 HTML 구조 분석

    Args:
        url: 분석할 뉴스 사이트 URL

    Returns:
        HTML 구조 분석 결과
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

        # TokenPost URL 체크
        if 'tokenpost' in url.lower():
            # TokenPost 전용 파싱
            result_data = {
                "url": url,
                "title": None,
                "published_date": None,
                "reporter_name": None,
                "article_content": None
            }

            # 1. 뉴스 제목 (title 태그)
            if soup.title:
                result_data['title'] = soup.title.string

            # 2. 발행 날짜 (<time> 태그)
            time_tag = soup.find('time')
            if time_tag:
                result_data['published_date'] = time_tag.get_text(strip=True)

            # 3. 기자 이름 (class="view_title_bottom_name")
            reporter_name = soup.find(class_='view_title_bottom_name')
            if reporter_name:
                result_data['reporter_name'] = reporter_name.get_text(strip=True)

            # 4. 본문 내용 (class="article_content")
            article_content = soup.find('div', class_='article_content')
            if article_content:
                result_data['article_content'] = article_content.get_text(strip=True)

            return {
                "status": "success",
                "message": "TokenPost 뉴스 데이터 추출 완료",
                "data": result_data
            }

        else:
            # 일반 URL - 전체 HTML 구조 분석
            structure_info = {
                "url": url,
                "title": soup.title.string if soup.title else None,
                "meta_tags": [],
                "headings": {},
                "paragraphs_count": len(soup.find_all('p')),
                "images_count": len(soup.find_all('img')),
                "links_count": len(soup.find_all('a')),
                "main_content_candidates": [],
                "article_candidates": []
            }

            # Meta 태그 추출
            for meta in soup.find_all('meta')[:10]:
                meta_info = {
                    "name": meta.get('name') or meta.get('property'),
                    "content": meta.get('content')
                }
                if meta_info['name']:
                    structure_info['meta_tags'].append(meta_info)

            # 제목 태그 분석
            for i in range(1, 7):
                headings = soup.find_all(f'h{i}')
                if headings:
                    structure_info['headings'][f'h{i}'] = [h.get_text(strip=True) for h in headings[:5]]

            # 주요 콘텐츠 후보 찾기
            content_candidates = soup.find_all(['article', 'main'])
            for elem in content_candidates[:3]:
                structure_info['article_candidates'].append({
                    'tag': elem.name,
                    'class': elem.get('class'),
                    'id': elem.get('id'),
                    'text_preview': elem.get_text(strip=True)[:200]
                })

            # div.content, div.article 등 찾기
            divs_with_content = soup.find_all('div', class_=lambda x: x and ('content' in str(x).lower() or 'article' in str(x).lower()))
            for div in divs_with_content[:3]:
                structure_info['main_content_candidates'].append({
                    'tag': div.name,
                    'class': div.get('class'),
                    'id': div.get('id'),
                    'text_preview': div.get_text(strip=True)[:200]
                })

            # 전체 HTML 미리보기 (script, style 제거)
            soup_copy = BeautifulSoup(soup.prettify(), 'html.parser')
            for script in soup_copy.find_all('script'):
                script.decompose()
            for style in soup_copy.find_all('style'):
                style.decompose()
            structure_info['html_preview'] = soup_copy.prettify()

            return {
                "status": "success",
                "message": "HTML 구조 분석 완료",
                "data": structure_info
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