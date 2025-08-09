from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.routers import api_router

load_dotenv()

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
