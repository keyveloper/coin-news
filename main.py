import os
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

# LangSmith 환경변수 직접 설정 (dotenv 로드 후)
if os.getenv("LANGSMITH_TRACING", "").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "default")
    print(f"[LangSmith] Tracing enabled - Project: {os.getenv('LANGCHAIN_PROJECT')}")

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
