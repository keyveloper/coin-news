# -*- coding: utf-8 -*-
"""Price Query Schema - Agent용 통합 가격 조회 파라미터"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class PriceQueryParams(BaseModel):
    """Agent가 가격 조회 시 사용할 통합 파라미터"""

    coin_name: str = Field(
        description="코인 심볼 (BTC, ETH, XRP 등)"
    )

    pivot_date: int = Field(
        description="기준 날짜 (epoch timestamp, 00:00:00)"
    )

    range_type: Literal["hour", "day", "week", "month", "year"] = Field(
        default="week",
        description="조회 범위 단위 (hour: ±1시간, day: 1일, week: 7일, month: 30일, year: 365일)"
    )

    direction: Literal["before", "after", "both"] = Field(
        default="before",
        description="기준일 대비 방향 (before: 과거, after: 미래, both: 양방향)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "BTC 7일 전 가격",
                    "value": {
                        "coin_name": "BTC",
                        "pivot_date": 1727740800,
                        "range_type": "week",
                        "direction": "before"
                    }
                },
                {
                    "description": "ETH 1개월 양방향 가격",
                    "value": {
                        "coin_name": "ETH",
                        "pivot_date": 1727740800,
                        "range_type": "month",
                        "direction": "both"
                    }
                }
            ]
        }


# 범위 오프셋 상수 (초 단위)
RANGE_OFFSETS = {
    "hour": 3600,           # 1시간
    "day": 86400,           # 1일
    "week": 7 * 86400,      # 7일
    "month": 30 * 86400,    # 30일
    "year": 365 * 86400,    # 365일
}
