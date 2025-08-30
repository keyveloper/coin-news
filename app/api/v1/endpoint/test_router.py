import logging
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query, HTTPException
from langchain_community.document_loaders import NewsURLLoader

from app.config.mongodb_config import get_mongodb_client
from app.config.chroma_config import get_chroma_client
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
    start_time = datetime.now()  # ⭐ 배치 시작 시각 기록

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
        local_db = mongodb_client.get_database("local")
        news_log_collection = local_db.get_collection("news.log")
        batch_log_collection = local_db.get_collection("batch.log")
        pivot_log_collection = local_db.get_collection("pivot.log")

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

        # -------------------------------------------------
        # 5. 실행 시간 로그 저장
        # -------------------------------------------------
        end_time = datetime.now()
        duration_sec = (end_time - start_time).total_seconds()

        batch_log = {
            "batch_name": "tokenpost",
            "pivot_date": pivot_date,
            "days_before": days_before,
            "started_at": start_time.isoformat(),
            "ended_at": end_time.isoformat(),
            "duration_sec": duration_sec,
            "links_collected": len(collected_links),
            "total_docs_loaded": len(all_documents),
            "saved_count": saved_count,
            "failed_count": failed_count
        }

        # -------------------------------------------------
        # 6. 가장 최신 pivot 시간 기록
        # -------------------------------------------------
        pivot_log_collection.insert_one({
            "batch_name": "tokenpost",
            "pivot_date": pivot_date,
            "created_at": datetime.now().isoformat()
        })

        batch_log_collection.insert_one(batch_log)

        logger.info(f"⭐ Batch execution time: {duration_sec}s logged successfully.")

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
            "batch_time_sec": duration_sec  # ⭐ 응답에도 실행 시간 포함
        }

    finally:
        release_lock()  # 🔓 무조건 락 해제


@test_router.get("/chromadb/all", response_model=dict)
def get_all_chromadb_data(
    limit: int = Query(100, description="Maximum number of documents to retrieve"),
    offset: int = Query(0, description="Number of documents to skip")
):
    """
    ChromaDB에 저장된 전체 데이터 조회

    Args:
        limit: 조회할 최대 문서 개수 (기본값: 100)
        offset: 건너뛸 문서 개수 (기본값: 0)

    Returns:
        ChromaDB에 저장된 문서들과 메타데이터
    """
    try:
        # Get ChromaDB client and collection
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection("coin_news")

        # Get total count
        total_count = collection.count()

        # Get all data with limit and offset (without embeddings)
        results = collection.get(
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"]
        )

        # Format results for better readability
        documents = []
        if results and results.get('documents'):
            for i in range(len(results['documents'])):
                doc_data = {
                    "id": results['ids'][i] if results.get('ids') else None,
                    "content": results['documents'][i],
                    "metadata": results['metadatas'][i] if results.get('metadatas') else {}
                }

                # Convert epoch to readable date if available
                if doc_data['metadata'].get('publish_date'):
                    try:
                        epoch_time = doc_data['metadata']['publish_date']
                        readable_date = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d %H:%M:%S")
                        doc_data['metadata']['publish_date_readable'] = readable_date
                    except:
                        pass

                documents.append(doc_data)

        return {
            "status": "success",
            "message": f"ChromaDB 데이터 조회 완료",
            "total_count": total_count,
            "returned_count": len(documents),
            "offset": offset,
            "limit": limit,
            "has_more": (offset + len(documents)) < total_count,
            "data": documents
        }

    except Exception as e:
        logger.error(f"Error retrieving ChromaDB data: {e}")
        raise HTTPException(status_code=500, detail=f"ChromaDB 조회 오류: {str(e)}")


@test_router.get("/chromadb/stats", response_model=dict)
def get_chromadb_stats():
    """
    ChromaDB 통계 정보 조회

    Returns:
        ChromaDB 컬렉션의 통계 정보
    """
    try:
        # Get ChromaDB client and collection
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection("coin_news")

        # Get basic stats
        total_count = collection.count()

        # Get sample data to analyze metadata structure
        sample = collection.get(limit=10, include=["metadatas"])

        # Analyze metadata fields
        metadata_fields = set()
        date_range = {"min": None, "max": None}

        if sample and sample.get('metadatas'):
            for metadata in sample['metadatas']:
                metadata_fields.update(metadata.keys())

                # Track date range
                if metadata.get('publish_date'):
                    try:
                        epoch = metadata['publish_date']
                        if date_range["min"] is None or epoch < date_range["min"]:
                            date_range["min"] = epoch
                        if date_range["max"] is None or epoch > date_range["max"]:
                            date_range["max"] = epoch
                    except:
                        pass

        # Convert epoch to readable dates
        if date_range["min"]:
            date_range["min_readable"] = datetime.fromtimestamp(date_range["min"]).strftime("%Y-%m-%d %H:%M:%S")
        if date_range["max"]:
            date_range["max_readable"] = datetime.fromtimestamp(date_range["max"]).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "status": "success",
            "collection_name": "coin_news",
            "total_documents": total_count,
            "metadata_fields": list(metadata_fields),
            "date_range": date_range
        }

    except Exception as e:
        logger.error(f"Error retrieving ChromaDB stats: {e}")
        raise HTTPException(status_code=500, detail=f"ChromaDB 통계 조회 오류: {str(e)}")


@test_router.get("/chromadb/by-epoch", response_model=dict)
def get_chromadb_by_epoch(
    date_epoch: int = Query(..., description="Target date as epoch timestamp (start of day, 00:00:00)"),
    top_k: int = Query(10, description="Number of results to return (default: 10)")
):
    """
    ChromaDB에서 특정 epoch time의 chunks 조회

    Args:
        date_epoch: 조회할 날짜의 epoch timestamp (하루의 시작 시간, 00:00:00)
        top_k: 반환할 결과 개수 (기본값: 10)

    Returns:
        해당 날짜의 뉴스 chunks

    Example:
        GET /test/chromadb/by-epoch?date_epoch=1763218800&top_k=10
        (2025-11-16 00:00:00)
    """
    try:
        from langchain_openai import OpenAIEmbeddings

        # Get ChromaDB client and collection
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection("coin_news")

        # Calculate date range (start and end of day)
        start_epoch = date_epoch
        end_epoch = date_epoch + 86399  # 23:59:59 of the same day

        # Convert to readable date
        date_readable = datetime.fromtimestamp(date_epoch).strftime("%Y-%m-%d %H:%M:%S")
        end_readable = datetime.fromtimestamp(end_epoch).strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"Searching ChromaDB for date_epoch={date_epoch} ({date_readable} to {end_readable})")

        # Create a dummy embedding for query (we just want to filter by date)
        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
        dummy_query = "bitcoin news"
        query_embedding = embeddings_model.embed_query(dummy_query)

        # Search with date filter using publish_date_epoch
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={
                "$and": [
                    {"publish_date_epoch": {"$gte": start_epoch}},
                    {"publish_date_epoch": {"$lte": end_epoch}}
                ]
            }
        )

        # Format results
        chunks = []
        if results and results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}

                # Add readable date to metadata
                if metadata.get('publish_date_epoch'):
                    try:
                        metadata['publish_date_readable'] = datetime.fromtimestamp(
                            metadata['publish_date_epoch']
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass

                chunk_data = {
                    "id": results['ids'][0][i] if results.get('ids') else None,
                    "content": doc,
                    "metadata": metadata,
                    "distance": results['distances'][0][i] if results['distances'] else None
                }
                chunks.append(chunk_data)

        return {
            "status": "success",
            "message": f"Found {len(chunks)} chunks for epoch {date_epoch}",
            "query_info": {
                "date_epoch": date_epoch,
                "date_readable": date_readable,
                "start_epoch": start_epoch,
                "end_epoch": end_epoch,
                "end_readable": end_readable,
                "top_k": top_k
            },
            "total_found": len(chunks),
            "data": chunks
        }

    except Exception as e:
        logger.error(f"Error searching ChromaDB by epoch: {e}")
        raise HTTPException(status_code=500, detail=f"ChromaDB epoch 조회 오류: {str(e)}")
