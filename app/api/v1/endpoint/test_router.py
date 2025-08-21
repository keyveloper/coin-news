import requests
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from bs4 import BeautifulSoup
from app.schemas.test import MyCustomResponse, MyCustomRequest
from app.services.naver_news_scratch_service import NaverNewsScratchService
from langchain_community.document_loaders import NewsURLLoader
from app.crawlers.tokenpost_page_crawler import TokenPostPageCrawler
from app.parser.coinreaders_parser import parse_coinreaders_news
from app.parser.tokenpost_parser import parse_tokenpost_news
from app.config.mongodb_config import get_mongodb_client
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import uuid

import logging

logger = logging.getLogger(__name__)

# In-memory task storage (for production, use Redis or DB)
task_results = {}

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

@test_router.post("/batch")
def get_docs_from_batch(
    query: str = Query(..., description="include in title"),
    pivot_date: str = Query(..., description="Reference date (YYYYMMDD format)"),
    days_before: int = Query(30, description="Number of days before pivot_date")
):
    """
    Simple batch test - Collect TokenPost news links within date range
    """


    # Parse pivot_date
    try:
        pivot_dt = datetime.strptime(pivot_date, "%Y%m%d")
        # Set to end of day (23:59:59) to include all news from pivot_date
        pivot_dt = pivot_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD")

    # Calculate cutoff date (start of day, days_before ago)
    cutoff_dt = pivot_dt - timedelta(days=days_before)
    cutoff_dt = cutoff_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    logger.info(f"Collecting news from {cutoff_dt} to {pivot_dt}")

    collected_links = []
    page = 1
    base_url = "https://www.tokenpost.kr/news/cryptocurrency"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    while True:
        try:
            # Fetch page
            url = f"{base_url}?page={page}"
            logger.info(f"Fetching page {page}: {url}")

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all articles
            list_left_item = soup.find('div', class_='list_left_item')
            if not list_left_item:
                logger.warning(f"No list_left_item found on page {page}")
                break

            articles = list_left_item.find_all('div', class_='list_left_item_article')
            if not articles:
                logger.warning(f"No articles found on page {page}")
                break

            logger.info(f"Found {len(articles)} articles on page {page}")

            found_in_range = 0
            should_stop = False

            for article in articles:
                try:
                    # Extract link from list_item_title
                    title_div = article.find('div', class_='list_item_title')
                    if not title_div:
                        continue

                    a_tag = title_div.find('a')
                    if not a_tag or not a_tag.get('href'):
                        continue

                    # Get title text
                    title_text = a_tag.get_text(strip=True)

                    # Filter by query - skip if query not in title
                    if query.lower() not in title_text.lower():
                        continue

                    link = a_tag.get('href')
                    if link.startswith('/'):
                        link = f"https://www.tokenpost.kr{link}"

                    # Extract datetime from time tag in list_item_write
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

                    # Parse datetime (format: "2025.11.17 22:18")
                    try:
                        news_dt = datetime.strptime(datetime_str, "%Y.%m.%d %H:%M")
                    except ValueError:
                        logger.warning(f"Failed to parse datetime: {datetime_str}")
                        continue

                    # Check if news is older than cutoff
                    if news_dt < cutoff_dt:
                        logger.info(f"Found news older than cutoff: {datetime_str}")
                        should_stop = True
                        break

                    # Check if news is within range
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

            logger.info(f"Page {page}: Found {found_in_range} news within range")

            # Stop if we found older news
            if should_stop:
                logger.info(f"Stopping at page {page} - reached cutoff date")
                break



            # Move to next page
            page += 1

        except Exception as e:
            logger.error(f"Error on page {page}: {e}")
            break

    # Step 2: Extract metadata using NewsURLLoader
    logger.info(f"Total {len(collected_links)} links collected. Starting metadata extraction...")

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

    # Extract only URLs from collected_links
    urls = [item["link"] for item in collected_links]

    # NewsURLLoader batch processing (max 20 URLs per batch to prevent timeout)
    batch_size = 20
    all_documents = []

    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(urls) + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_urls)} URLs)...")

        try:
            loader = NewsURLLoader(urls=batch_urls)
            docs = loader.load()

            # Convert to dict format
            for doc in docs:
                all_documents.append({
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                })

            logger.info(f"Batch {batch_num}/{total_batches} completed: {len(docs)} documents loaded")

        except Exception as e:
            logger.error(f"Error loading batch {batch_num}: {e}")
            # Continue with next batch even if one fails

    logger.info(f"Metadata extraction completed. Total documents: {len(all_documents)}")

    # Step 3: Save to MongoDB
    logger.info("Saving documents to MongoDB...")

    mongodb_client = get_mongodb_client()
    local_db = mongodb_client.get_database("local")
    news_log_collection = local_db.get_collection("news.log")

    saved = []
    saved_count = 0
    failed_count = 0

    for doc_data in all_documents:
        try:
            # Prepare document for MongoDB
            doc_dict = {
                "page_content": doc_data["page_content"],
                "metadata": doc_data["metadata"],
                "source": "tokenpost",
                "query": query,
                "collected_at": datetime.now().isoformat(),
                "pivot_date": pivot_date
            }

            # Check if document already exists (by URL)
            existing = news_log_collection.find_one({
                "metadata.url": doc_data["metadata"].get("url")
            })

            if existing:
                logger.info(f"Document already exists: {doc_data['metadata'].get('title', 'No title')[:50]}...")
                continue

            # Insert to MongoDB
            result = news_log_collection.insert_one(doc_dict)
            doc_dict['_id'] = str(result.inserted_id)
            saved.append(doc_dict)
            saved_count += 1
            logger.info(f"Saved to MongoDB: {doc_data['metadata'].get('title', 'No title')[:50]}...")

        except Exception as e:
            logger.error(f"Failed to save document: {e}")
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