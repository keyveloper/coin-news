import logging
import os
import requests
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Query, HTTPException
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

from app.config.mongodb_config import get_mongodb_client
from app.config.chroma_config import get_chroma_client

logger = logging.getLogger(__name__)

batch_route = APIRouter(prefix="/batch", tags=["batch"])


@batch_route.post("/embedding")
def embedding(
    query: str = Query(..., description="Search query to filter by title"),
    date: str = Query(..., description="Date to filter (YYYYMMDD format)"),
    row_size: int = Query(20, description="Maximum number of documents to process", ge=1, le=1000)
):
    try:
        # -------------------------------------------------
        # 1. Validate and parse date
        # -------------------------------------------------
        try:
            target_date = datetime.strptime(date, "%Y%m%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD")

        # Date range for the entire day (00:00:00 to 23:59:59)
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        logger.info(f"Searching for query='{query}', date={date}, row_size={row_size}")

        # -------------------------------------------------
        # 2. Connect to MongoDB
        # -------------------------------------------------
        mongodb_client = get_mongodb_client()
        local_db = mongodb_client.get_database("local")
        news_log_collection = local_db.get_collection("news.log")

        # -------------------------------------------------
        # 3. Build MongoDB query
        # -------------------------------------------------
        # Filter by query in title (case-insensitive) and date range
        mongo_query = {
            "metadata.title": {"$regex": query, "$options": "i"},  # Case-insensitive regex search
            "metadata.publish_date": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        }

        # -------------------------------------------------
        # 4. Execute query with limit
        # -------------------------------------------------
        cursor = news_log_collection.find(mongo_query).limit(row_size)
        documents = list(cursor)

        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        logger.info(f"Found {len(documents)} documents matching criteria")

        if not documents:
            return {
                "status": "success",
                "message": "No documents found matching criteria",
                "query": query,
                "date": date,
                "total_found": 0,
                "chunks_created": 0,
                "vectors_stored": 0
            }

        # -------------------------------------------------
        # 5. Initialize text splitter (RecursiveCharacterTextSplitter)
        # -------------------------------------------------
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

        # -------------------------------------------------
        # 6. Initialize OpenAI Embeddings
        # -------------------------------------------------
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not found in environment variables")

        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small"
        )

        # -------------------------------------------------
        # 7. Chunk documents
        # -------------------------------------------------
        all_chunks = []
        chunk_metadata_list = []

        for doc in documents:
            page_content = doc.get("page_content", "")
            metadata = doc.get("metadata", {})

            if not page_content:
                logger.warning(f"Empty page_content for document {doc.get('_id')}")
                continue

            # Split text into chunks
            chunks = text_splitter.split_text(page_content)

            # Prepare chunks with metadata
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{doc.get('_id', uuid4())}_{idx}"

                # Combine original metadata with chunk-specific info
                chunk_metadata = {
                    **metadata,  # Original metadata from MongoDB
                    "source": doc.get("source", "unknown"),
                    "collected_at": doc.get("collected_at", ""),
                    "pivot_date": doc.get("pivot_date", ""),
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "mongo_doc_id": doc.get("_id", "")
                }

                all_chunks.append(chunk)
                chunk_metadata_list.append({
                    "id": chunk_id,
                    "text": chunk,
                    "metadata": chunk_metadata
                })

        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")

        # -------------------------------------------------
        # 8. Generate embeddings for all chunks
        # -------------------------------------------------
        logger.info("Generating embeddings using OpenAI text-embedding-3-small...")
        embeddings = embeddings_model.embed_documents(all_chunks)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # -------------------------------------------------
        # 9. Store in ChromaDB
        # -------------------------------------------------
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection("coin_news")

        # Prepare data for ChromaDB
        ids = [item["id"] for item in chunk_metadata_list]
        documents_to_store = [item["text"] for item in chunk_metadata_list]
        metadatas = []

        # ChromaDB requires metadata values to be strings, ints, floats, or bools
        for item in chunk_metadata_list:
            meta = item["metadata"]
            # Convert all metadata values to strings for ChromaDB compatibility
            chroma_metadata = {
                "title": str(meta.get("title", "")),
                "link": str(meta.get("link", "")),
                "source": str(meta.get("source", "")),
                "language": str(meta.get("language", "")),
                "description": str(meta.get("description", "")),
                "publish_date": str(meta.get("publish_date", "")),
                "collected_at": str(meta.get("collected_at", "")),
                "pivot_date": str(meta.get("pivot_date", "")),
                "chunk_index": meta.get("chunk_index", 0),
                "total_chunks": meta.get("total_chunks", 0),
                "mongo_doc_id": str(meta.get("mongo_doc_id", "")),
                "query": query  # Add search query for tracking
            }
            metadatas.append(chroma_metadata)

        # Add to ChromaDB (use upsert to handle duplicates)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents_to_store,
            metadatas=metadatas
        )

        logger.info(f"Successfully stored {len(ids)} vectors in ChromaDB (upsert mode)")

        # -------------------------------------------------
        # 10. Return results
        # -------------------------------------------------
        return {
            "status": "success",
            "message": f"Successfully processed {len(documents)} documents",
            "query": query,
            "date": date,
            "row_size": row_size,
            "total_documents_found": len(documents),
            "total_chunks_created": len(all_chunks),
            "total_vectors_stored": len(embeddings),
            "chroma_collection": "coin_news",
            "embedding_model": "text-embedding-3-small"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch embedding endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@batch_route.post("/price")
def fetch_and_save_price_data(
    query: str = Query(..., description="Coin symbol (e.g., BTC, ETH)"),
    time: str = Query(..., description="Date in YYYYMMDD format")
):
    try:
        # -------------------------------------------------
        # 1. Validate and convert date to epoch timestamp
        # -------------------------------------------------
        try:
            target_date = datetime.strptime(time, "%Y%m%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD")

        # Convert to epoch timestamp (end of day)
        target_date_end = target_date.replace(hour=23, minute=59, second=59)
        epoch_timestamp = int(target_date_end.timestamp())

        # Format date for storage (YYYY-MM-DD)
        formatted_date = target_date.strftime("%Y-%m-%d")

        logger.info(f"Fetching price data for {query} on {formatted_date} (epoch: {epoch_timestamp})")

        # -------------------------------------------------
        # 2. Get CryptoCompare API key from environment
        # -------------------------------------------------
        api_key = os.getenv("CRYPTO_COMPARE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="CRYPTO_COMPARE_API_KEY not found in environment variables")

        # -------------------------------------------------
        # 3. Call CryptoCompare API
        # -------------------------------------------------
        api_url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            "fsym": query.upper(),  # From symbol (coin)
            "tsym": "USD",  # To symbol (fixed)
            "toTs": epoch_timestamp,  # End timestamp
            "limit": 24  # 24 hours of data
        }
        headers = {
            "authorization": f"Apikey {api_key}"
        }

        logger.info(f"Calling CryptoCompare API: {api_url} with params {params}")
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        api_data = response.json()

        # Check if API returned success
        if api_data.get("Response") != "Success":
            error_msg = api_data.get("Message", "Unknown error from CryptoCompare API")
            raise HTTPException(status_code=400, detail=f"CryptoCompare API error: {error_msg}")

        logger.info(f"Successfully fetched {len(api_data.get('Data', {}).get('Data', []))} price records")

        # -------------------------------------------------
        # 4. Save to MongoDB (price.log collection)
        # -------------------------------------------------
        mongodb_client = get_mongodb_client()
        local_db = mongodb_client.get_database("local")
        price_log_collection = local_db.get_collection("price.log")

        # Prepare documents for MongoDB (each hourly data point as a separate document)
        price_data_array = api_data.get("Data", {}).get("Data", [])
        price_documents = [
            {
                "coin_name": query.upper(),
                "date": formatted_date,
                "price_data": data,
                "created_at": datetime.now().isoformat()
            }
            for data in price_data_array
        ]

        # Insert multiple documents into MongoDB
        if price_documents:
            result = price_log_collection.insert_many(price_documents)
            logger.info(f"Saved {len(result.inserted_ids)} price records to MongoDB")
        else:
            logger.warning("No price data to save")
            result = None

        # -------------------------------------------------
        # 5. Return results
        # -------------------------------------------------
        return {
            "status": "success",
            "message": f"Successfully fetched and saved price data for {query}",
            "coin_name": query.upper(),
            "date": formatted_date,
            "epoch_timestamp": epoch_timestamp,
            "total_records": len(price_data_array),
            "documents_inserted": len(result.inserted_ids) if result else 0,
            "mongo_ids": [str(id) for id in result.inserted_ids[:5]] if result else [],  # First 5 IDs
            "data_preview": price_data_array[:3]  # First 3 records as preview
        }

    except HTTPException:
        raise
    except requests.RequestException as e:
        logger.error(f"API request error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from CryptoCompare API: {str(e)}")
    except Exception as e:
        logger.error(f"Error in price data endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
