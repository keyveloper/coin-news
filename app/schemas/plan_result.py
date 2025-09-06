"""Plan Result Schema for Executor Agent"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.vector_news import VectorNewsResult
from app.schemas.price import PriceData, PriceHourlyData


class PlanResult(BaseModel):
    """Result of executing a QueryPlan"""

    intent_type: str = Field(description="Intent type from QueryPlan")

    # Collected data by coin
    collected_coin_prices: Dict[str, List[PriceData]] = Field(
        default_factory=dict,
        description="Daily price data collected per coin. Key: coin_name (e.g., 'BTC'), Value: list of PriceData"
    )

    collected_coin_hourly_prices: Dict[str, List[PriceHourlyData]] = Field(
        default_factory=dict,
        description="Hourly price data collected per coin. Key: coin_name (e.g., 'BTC'), Value: list of PriceHourlyData"
    )

    collected_news_chunks: List[VectorNewsResult] = Field(
        default_factory=list,
        description="News articles collected from semantic searches"
    )

    # Metadata
    coin_names: List[str] = Field(
        default_factory=list,
        description="List of coins that were queried"
    )

    analysis_instructions: Optional[str] = Field(
        default=None,
        description="Instructions for how to analyze the collected data (optional)"
    )

    #semantice query:

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
                        {"date": "2024-12-01", "close": 42000.5, "time": 1733011200}
                    ]
                },
                "collected_coin_hourly_prices": {
                    "BTC": [
                        {"time": 1733011200, "high": 42500.0, "low": 41800.0, "open": 42100.0, "close": 42300.0}
                    ]
                },
                "collected_news_chunks": [
                    {"title": "Bitcoin surges...", "similarity_score": 0.85}
                ],
                "coin_names": ["BTC"],
                "analysis_instructions": None,
                "total_actions": 2,
                "successful_actions": 2,
                "failed_actions": 0,
                "errors": []
            }
        }
