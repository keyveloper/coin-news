from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequest(BaseModel):
    """
    Request model for chat endpoint
    """
    question: str = Field(..., description="User's question about cryptocurrency news")

class ChatResponse(BaseModel):
    """
    Response model for chat endpoint
    """
    answer: str = Field(..., description="Chatbot's answer to the question")

class ScrapeRequest(BaseModel):
    """
    Request model for scraping news
    """
    query: str = Field(default="cryptocurrency", description="Search query for news")
    num_articles: int = Field(default=10, ge=1, le=100, description="Number of articles to scrape")

class ScrapeResponse(BaseModel):
    """
    Response model for scrape endpoint
    """
    message: str = Field(..., description="Status message")
    num_articles: Optional[int] = Field(None, description="Number of articles scraped")

class MyCustomResponse(BaseModel):
    """
    Response model for testing
    """
    message: str = Field(..., description="Status message")

class MyCustomRequest(BaseModel):
    name: str
    age: int

class ChunkArticleRequest(BaseModel):
    content: str

class EmbeddingChunkRequest(BaseModel):
    chunks: List[str] = Field(..., description="List of text chunks to embed")