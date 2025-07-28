from fastapi import APIRouter
from app.models.schemas import MyCustomResponse, MyCustomRequest
from app.services.scraper import coin_news_scrape
from app.crawlers.coinnews_crawler import CoinNewsCrawler
from fastapi import Query

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

@test_router.get("/simple")
def get_simple():
    coin_news_scrape()
    return {"id": 1, "name": "J"}

@test_router.get("/crawl")
def get_crawl():
    """
    CoinNewsCrawler를 실행하여 coinness.com 크롤링 및 뉴스 URL 추출
    1. Selenium으로 URL 데이터 가져오기
    2. HTML에서 뉴스 URL 찾기
    3. title, url만 반환
    """
    try:
        # 크롤러 인스턴스 생성
        crawler = CoinNewsCrawler()
        result = crawler.crawl()

        return {
            "status": "success",
            "message": f"크롤링이 완료되었습니다.",
            "result": result
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"크롤링 중 오류 발생: {str(e)}",
            "traceback": traceback.format_exc()
        }