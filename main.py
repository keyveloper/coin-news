from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.test_route import test_router

load_dotenv()

app = FastAPI(
    title="Coin New Script Bot",
    description="Summarize Coin issue and crypto market",
    version="1.0.0"
)
app.include_router(test_router)


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
