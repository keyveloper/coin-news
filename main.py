import os

# 환경변수 먼저 로드 (LangChain import 전에!)
from dotenv import load_dotenv
load_dotenv(override=True)

# LangChain이 import되기 전에 환경변수 확인
print(f"[Startup] LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"[Startup] LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")

from fastapi import FastAPI
from app.api.routers import api_router

app = FastAPI(
    title="Coin New Script Bot",
    description="Summarize Coin issue and crypto market",
    version="1.0.0"
)

# API 라우터 등록
app.include_router(api_router)


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
