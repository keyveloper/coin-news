"""Normalized Query Schema for Query Analyzer"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Target(BaseModel):
    """Target entities and coins in the query"""
    coin: List[str] = Field(
        description="Coin symbols like BTC, ETH, XRP, or 'all'"
    )
    entity: Optional[List[str]] = Field(
        default=None,
        description="Subject who occurs events: country_name, corporation_name, committee_name, coin_market, or null"
    )

class Event(BaseModel):
    """Event information from the query"""
    magnitude: Optional[Literal["big", "small", "any"]] = Field(
        default=None,
        description="Event magnitude: big, small, any, or null"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords found in query"
    )

class Goal(BaseModel):
    """User's goal from the query"""
    task: Literal[
        "summarize",
        "analyze",
        "explain_impact",
        "find_reasons",
        "compare",
        "forecast",
        "extract_keywords"
    ] = Field(description="Task to perform")
    depth: Literal["short", "medium", "deep"] = Field(
        description="Analysis depth"
    )

class TimeRange(BaseModel):
    """Time range for the query"""
    pivot_time: Optional[str] = Field(
        default=None,
        description="Pivot time in format YYYYMMDD or 'today' or null"
    )
    relative: Optional[Literal["24h", "7d", "1m", "ytd", "all"]] = Field(
        default=None,
        description="Relative time range for vectorDB research - best range for researching"
    )

class Filters(BaseModel):
    """Filters for the query"""
    sentiment: Literal["positive", "negative", "neutral", "any"] = Field(
        default="any",
        description="Sentiment filter"
    )
    category: Literal[
        "macro",
        "altcoin",
        "defi",
        "layer2",
        "meme",
        "regulation",
        "exchange",
        "unknown"
    ] = Field(
        default="unknown",
        description="Category filter"
    )

class NormalizedQuery(BaseModel):
    """Structured query analysis result - single class with nested models"""
    # Main fields
    intent_type: Literal[
        "market_trend",
        "news_summary",
        "price_reason",
        "unknown"
    ] = Field(description="Type of user intent")

    target: Target = Field(description="Target coins and entities")
    event: Event = Field(description="Event information")
    goal: Goal = Field(description="User's goal")
    time_range: TimeRange = Field(description="Time range for analysis")
    filters: Filters = Field(default_factory=Filters, description="Additional filters")