from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.v1.endpoint.coinness_router import coinness_router
from app.api.v1.endpoint.test_router import test_router
from app.api.v1.endpoint.bloomingbit_router import bloomingbit_router
from app.api.v1.endpoint.naver_news_router import naver_news_router

load_dotenv()

app = FastAPI(
    title="Coin New Script Bot",
    description="Summarize Coin issue and crypto market",
    version="1.0.0"
)
app.include_router(test_router)
app.include_router(coinness_router)
app.include_router(bloomingbit_router)
app.include_router(naver_news_router)


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
