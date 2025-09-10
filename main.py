import os
from contextlib import asynccontextmanager

# 환경변수 먼저 로드 (LangChain import 전에!)
from dotenv import load_dotenv
load_dotenv(override=True)

# LangChain이 import되기 전에 환경변수 확인
print(f"[Startup] LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"[Startup] LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")

from fastapi import FastAPI
from chainlit.utils import mount_chainlit
from app.api.routers import api_router
from app.config.mongodb_config import get_mongodb_client
from app.config.chroma_config import get_chroma_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 DB 연결 관리"""
    # ==================== Startup ====================
    print("\n" + "="*50)
    print("[Startup] Initializing database connections...")
    print("="*50)

    # MongoDB 연결
    try:
        mongo_client = get_mongodb_client()
        mongo_client.get_client().admin.command('ping')
        print("[OK] MongoDB connected")
    except Exception as e:
        print(f"[FATAL] MongoDB connection failed: {e}")
        raise RuntimeError(f"MongoDB 연결 실패: {e}")

    # ChromaDB 연결
    try:
        chroma_client = get_chroma_client()
        chroma_client.get_client().heartbeat()
        print("[OK] ChromaDB connected")
    except Exception as e:
        print(f"[FATAL] ChromaDB connection failed: {e}")
        raise RuntimeError(f"ChromaDB 연결 실패: {e}")

    print("="*50)
    print("[Startup] All database connections ready!")
    print("="*50 + "\n")

    yield

    # ==================== Shutdown ====================
    print("\n[Shutdown] Closing database connections...")
    try:
        mongo_client.close()
        print("[OK] MongoDB connection closed")
    except Exception:
        pass
    print("[Shutdown] Server stopped\n")


app = FastAPI(
    title="Coin New Script Bot",
    description="Summarize Coin issue and crypto market",
    version="1.0.0",
    lifespan=lifespan
)

# API 라우터 등록
app.include_router(api_router)

# Chainlit 마운트 (/chat 경로)
mount_chainlit(app=app, target="cl_app.py", path="/chat")


@app.get("/")
async def root():
    return {
        "message": "🚀 Coin News Chatbot API is running!",
        "status": "healthy"
    }


# Health Check
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Debug: 환경변수 확인용
@app.get("/debug/env")
async def debug_env():
    return {
        "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
        "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT"),
        "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY", "")[:20] + "..." if os.getenv("LANGCHAIN_API_KEY") else None
    }
