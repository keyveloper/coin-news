from fastapi import APIRouter

from app.crawlers.coinness_crawler import CoinnessCrawler

coinness_router = APIRouter(prefix="/coinness", tags=["coinness"])

@coinness_router.get("/news-list")
def get_news_list():
    """
    CoinNewsCrawler를 실행하여 coinness.com 크롤링 및 뉴스 URL 추출
    1. Selenium으로 URL 데이터 가져오기
    2. HTML에서 뉴스 URL 찾기
    3. title, url만 반환
    """
    try:
        # 크롤러 인스턴스 생성
        crawler = CoinnessCrawler()
        result = crawler.get_news_list()

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


@coinness_router.get("/news-to-vector-db")
def news_to_vector_db():
    """
    new-list의 각 news들을 돌면서 vector DB에 넣어보기
    ⚒️ 다양한 chunking 전략 사용하기
    :return:
    """
