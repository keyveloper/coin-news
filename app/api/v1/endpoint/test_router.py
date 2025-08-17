import requests
from fastapi import APIRouter, Query, HTTPException
from bs4 import BeautifulSoup
from app.schemas.test import MyCustomResponse, MyCustomRequest
from app.services.naver_news_scratch_service import NaverNewsScratchService

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

@test_router.get("/scratch", response_model=dict)
def get_scratch(query: str):
    service = NaverNewsScratchService()
    docs = service.scratch_adn_save_to_mongodb(query)
    return docs