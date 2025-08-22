import logging
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query, HTTPException
from langchain_community.document_loaders import NewsURLLoader

from app.config.mongodb_config import get_mongodb_client
from app.schemas.test import MyCustomResponse, MyCustomRequest
from app.services.naver_news_scratch_service import NaverNewsScratchService
from app.tmp.batch_lock import acquire_lock, release_lock

logger = logging.getLogger(__name__)

# In-memory task storage (for production, use Redis or DB)
task_results = {}

test_router = APIRouter(prefix="/test", tags=["test"])


@test_router.get("", response_model=MyCustomResponse)
def get_test(name: str = Query(
    ...,  # required parameter
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

@test_router.post("/batch")
def get_docs_from_batch(
        pivot_date: str = Query(..., description="Reference date (YYYYMMDD format)"),
        days_before: int = Query(30, description="Number of days before pivot_date")
):
    """
    Simple batch test - Collect TokenPost news links within date range
    """

    acquire_lock()  # 🔒 락 획득

    try:
        # -------------------------------------------------
        # 1. 날짜 파싱
        # -------------------------------------------------
        try:
            pivot_dt = datetime.strptime(pivot_date, "%Y%m%d")
            pivot_dt = pivot_dt.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD")

        cutoff_dt = pivot_dt - timedelta(days=days_before)
        cutoff_dt = cutoff_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        logger.info(f"Collecting news from {cutoff_dt} to {pivot_dt}")

        # -------------------------------------------------
        # 2. 링크 크롤링
        # -------------------------------------------------
        collected_links = []
        page = 1
        base_url = "https://www.tokenpost.kr/news/cryptocurrency"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        while True:
            try:
                url = f"{base_url}?page={page}"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')
                list_left_item = soup.find('div', class_='list_left_item')

                if not list_left_item:
                    logger.warning(f"No list_left_item found on page {page}")
                    break

                articles = list_left_item.find_all('div', class_='list_left_item_article')
                if not articles:
                    logger.warning(f"No articles found on page {page}")
                    break

                found_in_range = 0
                should_stop = False

                for article in articles:
                    try:
                        title_div = article.find('div', class_='list_item_title')
                        if not title_div:
                            continue

                        a_tag = title_div.find('a')
                        if not a_tag or not a_tag.get('href'):
                            continue

                        link = a_tag.get('href')
                        if link.startswith('/'):
                            link = f"https://www.tokenpost.kr{link}"

                        write_div = article.find('div', class_='list_item_write')
                        if not write_div:
                            continue

                        date_item = write_div.find('div', class_='date_item')
                        if not date_item:
                            continue

                        time_tag = date_item.find('time', class_='day')
                        if not time_tag or not time_tag.get('datetime'):
                            continue

                        datetime_str = time_tag.get('datetime')

                        try:
                            news_dt = datetime.strptime(datetime_str, "%Y.%m.%d %H:%M")
                        except ValueError:
                            logger.warning(f"Failed to parse datetime: {datetime_str}")
                            continue

                        if news_dt < cutoff_dt:
                            should_stop = True
                            break

                        if cutoff_dt <= news_dt <= pivot_dt:
                            collected_links.append({
                                "link": link,
                                "datetime": datetime_str,
                                "title": a_tag.get_text(strip=True)
                            })
                            found_in_range += 1

                    except Exception as e:
                        logger.error(f"Error parsing article: {e}")
                        continue

                if should_stop:
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                break

        # -------------------------------------------------
        # 3. 메타데이터 로딩 (NewsURLLoader)
        # -------------------------------------------------
        if not collected_links:
            return {
                "status": "success",
                "message": "No links found matching criteria",
                "pivot_date": pivot_date,
                "days_before": days_before,
                "cutoff_date": cutoff_dt.strftime("%Y.%m.%d"),
                "total_pages_crawled": page,
                "total_links_collected": 0,
                "documents": []
            }

        urls = [item["link"] for item in collected_links]
        batch_size = 20
        all_documents = []

        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i+batch_size]
            batch_num = (i // batch_size) + 1

            try:
                loader = NewsURLLoader(urls=batch_urls)
                docs = loader.load()

                for doc in docs:
                    all_documents.append({
                        "page_content": doc.page_content,
                        "metadata": doc.metadata
                    })

            except Exception as e:
                logger.error(f"Error loading batch {batch_num}: {e}")

        # -------------------------------------------------
        # 4. MongoDB 저장
        # -------------------------------------------------
        mongodb_client = get_mongodb_client()
        news_log_collection = mongodb_client.local.get_collection("news.log")

        saved = []
        saved_count = 0
        failed_count = 0

        for doc_data in all_documents:
            try:
                metadata = doc_data.get("metadata", {})

                doc_dict = {
                    "page_content": doc_data["page_content"],
                    "metadata": metadata,
                    "source": "tokenpost",
                    "collected_at": datetime.now().isoformat(),
                    "pivot_date": pivot_date
                }

                result = news_log_collection.insert_one(doc_dict)
                doc_dict["_id"] = str(result.inserted_id)

                saved.append(doc_dict)
                saved_count += 1

            except Exception as e:
                logger.error(f"❌ Failed to save document: {e}")
                failed_count += 1

        logger.info(f"MongoDB save completed - Success: {saved_count}, Failed: {failed_count}")

        return {
            "status": "success",
            "message": f"Successfully collected {len(all_documents)} documents, saved {saved_count} to MongoDB",
            "pivot_date": pivot_date,
            "days_before": days_before,
            "cutoff_date": cutoff_dt.strftime("%Y.%m.%d"),
            "total_pages_crawled": page,
            "total_links_collected": len(collected_links),
            "total_documents_loaded": len(all_documents),
            "saved_to_mongodb": saved_count,
            "failed_to_save": failed_count,
            "already_exists": len(all_documents) - saved_count - failed_count,
            "documents": all_documents
        }

    finally:
        release_lock()  # 🔓 무조건 락 해제
