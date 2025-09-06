"""Price Schema - MongoDB 가격 데이터 스키마"""
from typing import Optional
from pydantic import BaseModel, Field


class PriceData(BaseModel):
    """
    PriceRepository에서 반환하는 가격 데이터 스키마

    모든 _get_daily_close_values() 기반 메서드들의 결과 형식:
    - find_by_coin_name_with_oneday()
    - find_by_coin_name_with_week_before()
    - find_by_coin_name_with_week_after()
    - find_by_coin_name_with_month_before()
    - find_by_coin_name_with_month_after()
    - find_by_coin_name_with_year()
    - find_by_coin()
    """
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    close: float = Field(..., description="종가")
    time: Optional[int] = Field(None, description="타임스탬프 (epoch time)")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-12-01",
                "close": 42000.50,
                "time": 1733097599
            }
        }


class PriceHourlyData(BaseModel):
    """
    find_by_coin_name_with_hour_range() 결과 형식 - 시간별 상세 가격 데이터
    """
    time: Optional[int] = Field(None, description="타임스탬프 (epoch time)")
    high: Optional[float] = Field(None, description="최고가")
    low: Optional[float] = Field(None, description="최저가")
    open: Optional[float] = Field(None, description="시가")
    close: Optional[float] = Field(None, description="종가")

    class Config:
        json_schema_extra = {
            "example": {
                "time": 1733011200,
                "high": 42500.00,
                "low": 41800.00,
                "open": 42100.00,
                "close": 42300.00
            }
        }
