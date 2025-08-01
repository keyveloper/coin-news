from fastapi import APIRouter, Depends

from app.crawlers.bloomingbit_crawler import BloomingbitCrawler
from app.models.schemas import MyCustomResponse

bloomingbit_router = APIRouter(prefix="/bloomingbit", tags=["bloomingbit"])

# 싱글톤 인스턴스를 반환하는 의존성 함수
_crawler_instance = None

def get_bloomingbit_crawler() -> BloomingbitCrawler:
    """
    BloomingbitCrawler 싱글톤 인스턴스 반환
    FastAPI Depends를 통해 주입됨
    """
    global _crawler_instance
    if _crawler_instance is None:
        _crawler_instance = BloomingbitCrawler()
    return _crawler_instance


@bloomingbit_router.get("/soup")
def get_soup(crawler: BloomingbitCrawler = Depends(get_bloomingbit_crawler)):
    """
    BeautifulSoup 객체 반환 (테스트용)
    """
    try:
        soup = crawler.get_soup()
        return {
            "status": "success",
            "message": "Soup 객체 크롤링 완료",
            "soup": str(soup)
        }
    except Exception as error:
        import traceback
        return {
            "status": "error",
            "message": f"크롤링 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }

@bloomingbit_router.get("/ranking-news-urls")
def get_ranking_news_urls(crawler: BloomingbitCrawler = Depends(get_bloomingbit_crawler)):
    """
    rankingNewsSwiper에서 랭킹 뉴스 URL과 제목 추출
    """
    try:
        ranking_news = crawler.get_ranking_news_urls()

        return {
            "status": "success",
            "message": f"{len(ranking_news)}개의 랭킹 뉴스를 가져왔습니다.",
            "count": len(ranking_news),
            "data": ranking_news
        }
    except Exception as error:
        import traceback
        return {
            "status": "error",
            "message": f"랭킹 뉴스 크롤링 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }


@bloomingbit_router.get("/news-list", response_model=MyCustomResponse)
def get_news_list(crawler: BloomingbitCrawler = Depends(get_bloomingbit_crawler)):
    """
    뉴스 리스트 크롤링 및 반환
    """
    try:
        result = ""

        return {
            "status": "success",
            "message": f"크롤링이 완료되었습니다.",
            "result": result,
        }
    except Exception as error:
        import traceback
        return {
            "status": "error",
            "message": f"크롤링 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }
