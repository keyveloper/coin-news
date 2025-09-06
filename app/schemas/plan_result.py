"""Plan Result Schema for Executor Agent"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NewsChunk(BaseModel):
    """Single news article data"""
    title: Optional[str] = None
    content: Optional[str] = None
    published_date: Optional[str] = None
    url: Optional[str] = None
    similarity_score: Optional[float] = None


class CoinPrice(BaseModel):
    """Single price data point"""
    timestamp: int = Field(description="Unix timestamp")
    date: Optional[str] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float = Field(description="Closing price")
    volume: Optional[float] = None


class PlanResult(BaseModel):
    """Result of executing a TaskPlan"""

    intent_type: str = Field(description="Intent type from TaskPlan")

    # Collected data by coin
    collected_coin_prices: Dict[str, List[CoinPrice]] = Field(
        default_factory=dict,
        description="Price data collected per coin. Key: coin_name (e.g., 'BTC'), Value: list of price data"
    )

    collected_news_chunks: List[NewsChunk] = Field(
        default_factory=list,
        description="News articles collected from searches"
    )

    # Metadata
    coin_names: List[str] = Field(
        default_factory=list,
        description="List of coins that were queried"
    )

    analysis_instructions: str = Field(
        description="Instructions for how to analyze the collected data"
    )

    # Execution statistics
    total_actions: int = Field(description="Total number of tool calls")
    successful_actions: int = Field(description="Number of successful tool calls")
    failed_actions: int = Field(description="Number of failed tool calls")

    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages if any tools failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "intent_type": "market_trend",
                "collected_coin_prices": {
                    "BTC": [
                        {"timestamp": 1733011200, "close": 42000.5, "high": 42500.0, "low": 41800.0}
                    ]
                },
                "collected_news_chunks": [
                    {"title": "Bitcoin surges...", "similarity_score": 0.85}
                ],
                "coin_names": ["BTC"],
                "analysis_instructions": "Analyze weekly trends...",
                "total_actions": 2,
                "successful_actions": 2,
                "failed_actions": 0,
                "errors": []
            }
        }
