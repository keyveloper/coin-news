from fastapi import APIRouter, Depends
import traceback
from app.crawlers.bloomingbit_crawler import BloomingbitCrawler
from app.schemas.schemas import MyCustomResponse, ChunkArticleRequest, EmbeddingChunkRequest, QueryRequest
# Chunking libraries
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)
import tiktoken
# Embedding
from langchain_community.embeddings import HuggingFaceEmbeddings
# ChromaDB
import chromadb
from chromadb.config import Settings

bloomingbit_router = APIRouter(prefix="/bloomingbit", tags=["bloomingbit"])

# 싱글톤 인스턴스를 반환하는 의존성 함수
_crawler_instance = None
_embedding_model = None

def get_bloomingbit_crawler() -> BloomingbitCrawler:
    """
    BloomingbitCrawler 싱글톤 인스턴스 반환
    FastAPI Depends를 통해 주입됨
    """
    global _crawler_instance
    if _crawler_instance is None:
        _crawler_instance = BloomingbitCrawler()
    return _crawler_instance

def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    HuggingFaceEmbeddings 싱글톤 인스턴스 반환
    다국어 지원 모델 사용 (한국어 포함)
    """
    global _embedding_model
    if _embedding_model is None:
        # 다국어 지원 임베딩 모델 (한국어, 영어 모두 지원)
        _embedding_model = HuggingFaceEmbeddings(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    return _embedding_model


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
        return {
            "status": "error",
            "message": f"랭킹 뉴스 크롤링 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }

@bloomingbit_router.get("/article-soup")
def get_article_soup(crawler: BloomingbitCrawler = Depends(get_bloomingbit_crawler)):
    try:
        article_soup = crawler.get_soup("https://bloomingbit.io/feed/news/99546")
        return {
            "status": "success",
            "message": "Soup 객체 크롤링 완료",
            "soup": str(article_soup)
        }
    except Exception as error:
        return {
            "status": "error",
            "message": f"get_article_soup  오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }

@bloomingbit_router.get("/extracted-metadata")
def extract_metadata(crawler: BloomingbitCrawler = Depends()):
    try:
        result = crawler.extract_article_metadata("https://bloomingbit.io/feed/news/99546")

        return {
            "status": "success",
            "message": f"extract-metadata크롤링이 완료되었습니다.",
            "result": result,
        }
    except Exception as error:
        return {
            "status": "error",
            "message": f"extract-metadata 크롤링 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }

@bloomingbit_router.post("/chunking/article")
def chunk_article(request: ChunkArticleRequest):
    """
    다양한 Chunking 전략으로 텍스트 분할 테스트
    """
    try:
        content = request.content
        results = {}

        # === 1. RecursiveCharacterTextSplitter (가장 추천) ===
        print("=" * 50)
        print("1. RecursiveCharacterTextSplitter (LangChain)")
        print("=" * 50)

        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        recursive_chunks = recursive_splitter.split_text(content)
        results['recursive_character_splitter'] = {
            "description": "계층적으로 분할 (문단 → 문장 → 단어). RAG에 가장 적합",
            "chunk_count": len(recursive_chunks),
            "chunks": recursive_chunks,
            "avg_chunk_length": sum(len(c) for c in recursive_chunks) / len(recursive_chunks) if recursive_chunks else 0
        }
        print(f"청크 개수: {len(recursive_chunks)}")

        # === 2. CharacterTextSplitter ===
        print("\n" + "=" * 50)
        print("2. CharacterTextSplitter (LangChain)")
        print("=" * 50)

        char_splitter = CharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separator="\n"
        )
        char_chunks = char_splitter.split_text(content)
        results['character_splitter'] = {
            "description": "단일 구분자로 분할 (예: 개행문자)",
            "chunk_count": len(char_chunks),
            "chunks": char_chunks,
            "avg_chunk_length": sum(len(c) for c in char_chunks) / len(char_chunks) if char_chunks else 0
        }
        print(f"청크 개수: {len(char_chunks)}")

        # === 3. TokenTextSplitter (OpenAI 토큰 기반) ===
        print("\n" + "=" * 50)
        print("3. TokenTextSplitter (LangChain + tiktoken)")
        print("=" * 50)

        token_splitter = TokenTextSplitter(
            chunk_size=200,  # 토큰 단위
            chunk_overlap=20
        )
        token_chunks = token_splitter.split_text(content)
        results['token_splitter'] = {
            "description": "OpenAI 토큰 기반 분할 (GPT 모델에 최적)",
            "chunk_count": len(token_chunks),
            "chunks": token_chunks,
            "avg_chunk_length": sum(len(c) for c in token_chunks) / len(token_chunks) if token_chunks else 0
        }
        print(f"청크 개수: {len(token_chunks)}")

        # === 4. tiktoken 직접 사용 ===
        print("\n" + "=" * 50)
        print("4. tiktoken (OpenAI 공식)")
        print("=" * 50)

        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        tokens = encoding.encode(content)
        token_count = len(tokens)

        # 토큰을 청크로 나누기
        chunk_size_tokens = 200
        tiktoken_chunks = []
        for i in range(0, len(tokens), chunk_size_tokens):
            chunk_tokens = tokens[i:i + chunk_size_tokens]
            chunk_text = encoding.decode(chunk_tokens)
            tiktoken_chunks.append(chunk_text)

        results['tiktoken_direct'] = {
            "description": "OpenAI tiktoken으로 직접 토큰화 후 분할",
            "total_tokens": token_count,
            "chunk_count": len(tiktoken_chunks),
            "chunks": tiktoken_chunks,
            "avg_tokens_per_chunk": token_count / len(tiktoken_chunks) if tiktoken_chunks else 0
        }
        print(f"총 토큰 수: {token_count}")
        print(f"청크 개수: {len(tiktoken_chunks)}")

        # === 5. 단순 문장 분할 (기본) ===
        print("\n" + "=" * 50)
        print("5. Simple Sentence Splitter (기본)")
        print("=" * 50)

        simple_chunks = content.split('. ')
        simple_chunks = [c.strip() + '.' for c in simple_chunks if c.strip()]
        results['simple_sentence'] = {
            "description": "마침표 기준 문장 단위 분할",
            "chunk_count": len(simple_chunks),
            "chunks": simple_chunks,
            "avg_chunk_length": sum(len(c) for c in simple_chunks) / len(simple_chunks) if simple_chunks else 0
        }
        print(f"청크 개수: {len(simple_chunks)}")

        # === 요약 통계 ===
        summary = {
            "original_text_length": len(content),
            "methods_tested": len(results),
            "recommendations": {
                "for_rag": "recursive_character_splitter - 의미 단위 보존",
                "for_openai": "token_splitter or tiktoken_direct - 토큰 제한 관리",
                "for_simple": "simple_sentence - 빠르고 간단"
            }
        }

        print("\n" + "=" * 50)
        print("Chunking 테스트 완료!")
        print("=" * 50)

        return {
            "status": "success",
            "message": "5가지 chunking 전략으로 텍스트 분할 완료",
            "summary": summary,
            "results": results
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"Chunking 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }


@bloomingbit_router.post("/embedding-chunk")
def embed_chunk(
    request: EmbeddingChunkRequest,
    embeddings_model: HuggingFaceEmbeddings = Depends(get_embedding_model)
):
    """
    텍스트 청크 리스트를 임베딩 벡터로 변환 (LangChain)

    Args:
        request: chunks 필드에 문자열 리스트 포함
        embeddings_model: HuggingFaceEmbeddings 모델 (자동 주입)

    Returns:
        embeddings: 각 청크에 대한 임베딩 벡터 리스트
        model_info: 사용된 모델 정보
        statistics: 임베딩 통계
    """
    try:
        chunks = request.chunks

        if not chunks:
            return {
                "status": "error",
                "message": "청크 리스트가 비어있습니다.",
                "data": None
            }

        # LangChain의 embed_documents 메서드 사용
        embeddings_list = embeddings_model.embed_documents(chunks)

        # 통계 정보
        statistics = {
            "total_chunks": len(chunks),
            "embedding_dimension": len(embeddings_list[0]) if embeddings_list else 0,
            "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
            "avg_chunk_length": sum(len(c) for c in chunks) / len(chunks) if chunks else 0
        }

        return {
            "status": "success",
            "message": f"{len(chunks)}개의 청크를 임베딩으로 변환 완료",
            "data": {
                "embeddings": embeddings_list,
                "statistics": statistics,
                "model_info": {
                    "name": "paraphrase-multilingual-MiniLM-L12-v2",
                    "description": "다국어 지원 임베딩 모델 (한국어, 영어 등 50+ 언어)",
                    "dimension": statistics["embedding_dimension"],
                    "max_sequence_length": 128
                }
            }
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"임베딩 생성 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }

@bloomingbit_router.get("/vectorDB")
def save_to_vector_db(
    url: str = "https://bloomingbit.io/feed/news/99554",
    crawler: BloomingbitCrawler = Depends(get_bloomingbit_crawler),
    embeddings_model: HuggingFaceEmbeddings = Depends(get_embedding_model)
):
    """
    뉴스 기사를 크롤링 → 메타데이터 추출 → 청킹 → 임베딩 → ChromaDB 저장

    Args:
        url: 크롤링할 뉴스 기사 URL
        crawler: BloomingbitCrawler 인스턴스
        embeddings_model: HuggingFaceEmbeddings 모델

    Returns:
        저장 성공 여부와 저장된 데이터 정보
    """
    try:
        # 1. 메타데이터 추출
        print(f"[1/4] 메타데이터 추출 중... URL: {url}")
        metadata = crawler.extract_article_metadata(url)
        content = metadata.get('content', '')

        if not content:
            return {
                "status": "error",
                "message": "기사 본문을 가져올 수 없습니다.",
                "data": None
            }

        # 2. 청킹 (RecursiveCharacterTextSplitter 사용)
        print(f"[2/4] 청킹 중... 원본 텍스트 길이: {len(content)}")
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = recursive_splitter.split_text(content)
        print(f"생성된 청크 개수: {len(chunks)}")

        # 3. 임베딩 생성
        print(f"[3/4] 임베딩 생성 중...")
        embeddings_list = embeddings_model.embed_documents(chunks)
        print(f"임베딩 벡터 차원: {len(embeddings_list[0])}")

        # 4. ChromaDB에 저장
        print(f"[4/4] ChromaDB에 저장 중...")

        # ChromaDB 클라이언트 생성
        chroma_client = chromadb.PersistentClient(
            path="./chroma_db",  # 데이터 저장 경로
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 컬렉션 생성 또는 가져오기
        collection_name = "bloomingbit_news"
        try:
            collection = chroma_client.get_collection(name=collection_name)
            print(f"기존 컬렉션 '{collection_name}' 사용")
        except:
            collection = chroma_client.create_collection(
                name=collection_name,
                metadata={"description": "Bloomingbit 뉴스 기사 임베딩"}
            )
            print(f"새 컬렉션 '{collection_name}' 생성")

        # 메타데이터 준비 (각 청크마다)
        metadatas = []
        ids = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "source_url": url,
                "title": metadata.get('title') or '',
                "author": metadata.get('author') or '',
                "published_date": metadata.get('published_date') or '',
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_text": chunk[:200]  # 미리보기용 (처음 200자)
            }

            # ChromaDB는 None 값을 허용하지 않으므로 None 값 제거
            chunk_metadata = {k: v for k, v in chunk_metadata.items() if v is not None and v != ''}

            # 필수 필드는 유지 (chunk_index, total_chunks)
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            chunk_metadata["source_url"] = url

            metadatas.append(chunk_metadata)

            # 고유 ID 생성 (URL + 청크 인덱스)
            article_id = url.split('/')[-1]  # 예: 99546
            ids.append(f"{article_id}_chunk_{i}")

        # ChromaDB에 데이터 저장
        collection.add(
            embeddings=embeddings_list,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ ChromaDB 저장 완료! 총 {len(chunks)}개 청크 저장됨")

        # 저장된 데이터 확인
        collection_count = collection.count()

        return {
            "status": "success",
            "message": f"ChromaDB에 {len(chunks)}개의 청크를 성공적으로 저장했습니다.",
            "data": {
                "url": url,
                "title": metadata.get('title', ''),
                "total_chunks": len(chunks),
                "embedding_dimension": len(embeddings_list[0]),
                "collection_name": collection_name,
                "collection_total_count": collection_count,
                "saved_ids": ids,
                "sample_metadata": metadatas[0] if metadatas else None
            }
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"Vector DB 저장 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }


@bloomingbit_router.post("/query")
def get_by_query(
    request: QueryRequest,
    embeddings_model: HuggingFaceEmbeddings = Depends(get_embedding_model)
):
    """
    사용자 쿼리를 기반으로 ChromaDB에서 관련 뉴스 검색 (Semantic Search)

    Args:
        request: 사용자 검색 쿼리
        embeddings_model: HuggingFaceEmbeddings 모델

    Returns:
        관련도가 높은 뉴스 청크와 메타데이터 반환
    """
    try:
        query = request.query

        if not query or query.strip() == '':
            return {
                "status": "error",
                "message": "검색 쿼리가 비어있습니다.",
                "data": None
            }

        print(f"[1/3] 검색 쿼리: {query}")

        # 1. 쿼리를 임베딩으로 변환
        print(f"[2/3] 쿼리 임베딩 생성 중...")
        query_embedding = embeddings_model.embed_query(query)
        print(f"임베딩 벡터 차원: {len(query_embedding)}")

        # 2. ChromaDB 클라이언트 생성 및 컬렉션 가져오기
        print(f"[3/3] ChromaDB에서 유사한 문서 검색 중...")
        chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 컬렉션 가져오기
        collection_name = "bloomingbit_news"
        try:
            collection = chroma_client.get_collection(name=collection_name)
        except Exception as e:
            return {
                "status": "error",
                "message": f"컬렉션 '{collection_name}'을 찾을 수 없습니다. 먼저 /vectorDB 엔드포인트로 데이터를 저장하세요.",
                "data": None
            }

        # 3. 유사도 검색 (상위 5개 결과 반환)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,  # 상위 5개 결과
            include=["documents", "metadatas", "distances"]
        )

        # 4. 결과 포맷팅
        if not results['ids'] or len(results['ids'][0]) == 0:
            return {
                "status": "success",
                "message": "검색 결과가 없습니다.",
                "data": {
                    "query": query,
                    "total_results": 0,
                    "results": []
                }
            }

        # 검색 결과를 보기 좋게 포맷팅
        formatted_results = []
        for i in range(len(results['ids'][0])):
            result_item = {
                "rank": i + 1,
                "id": results['ids'][0][i],
                "similarity_score": 1 - results['distances'][0][i],  # distance를 similarity로 변환
                "distance": results['distances'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i]
            }
            formatted_results.append(result_item)

        # 5. 기사별로 그룹핑 (같은 기사의 여러 청크를 그룹화)
        articles = {}
        for result in formatted_results:
            source_url = result['metadata'].get('source_url', 'unknown')
            if source_url not in articles:
                articles[source_url] = {
                    "source_url": source_url,
                    "title": result['metadata'].get('title', '제목 없음'),
                    "author": result['metadata'].get('author', '작성자 미상'),
                    "published_date": result['metadata'].get('published_date', '날짜 미상'),
                    "relevant_chunks": [],
                    "max_similarity": 0
                }

            articles[source_url]['relevant_chunks'].append({
                "rank": result['rank'],
                "chunk_index": result['metadata'].get('chunk_index', 0),
                "similarity_score": result['similarity_score'],
                "content": result['content']
            })

            # 최고 유사도 업데이트
            if result['similarity_score'] > articles[source_url]['max_similarity']:
                articles[source_url]['max_similarity'] = result['similarity_score']

        # 유사도 순으로 정렬
        sorted_articles = sorted(
            articles.values(),
            key=lambda x: x['max_similarity'],
            reverse=True
        )

        print(f"✅ 검색 완료! {len(formatted_results)}개의 청크를 찾았습니다.")

        return {
            "status": "success",
            "message": f"'{query}' 관련 검색 결과 {len(formatted_results)}개를 찾았습니다.",
            "data": {
                "query": query,
                "total_results": len(formatted_results),
                "total_articles": len(articles),
                "detailed_chunks": formatted_results,  # 개별 청크 상세 정보
                "grouped_by_article": sorted_articles  # 기사별 그룹화
            }
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"검색 중 오류 발생: {str(error)}",
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
        return {
            "status": "error",
            "message": f"크롤링 중 오류 발생: {str(error)}",
            "traceback": traceback.format_exc()
        }
