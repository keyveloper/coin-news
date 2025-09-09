"""
MongoDB 가격 데이터 저장소
"""
from typing import Optional, List, Dict, Union, Literal
from datetime import datetime, timedelta
from pymongo.database import Database
from pymongo.collection import Collection
from app.config.mongodb_config import get_mongodb_client
from app.schemas.price import PriceData, PriceHourlyData
from app.schemas.price_query import RANGE_OFFSETS


class PriceRepository:
    """가격 데이터 저장소 (Singleton Pattern)"""
    _instance: Optional["PriceRepository"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 이미 초기화된 경우 중복 초기화 방지
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True

        # 데이터베이스 및 컬렉션 이름 설정
        self._database_name = "local"
        self._collection_name = "price.log"

        # MongoDB 클라이언트 연결
        self.mongo_client = get_mongodb_client()
        self.db: Database = self.mongo_client.get_database(self._database_name)
        self.collection: Collection = self.db[self._collection_name]

        print(f"[OK] PriceRepository initialized (DB: {self._database_name}, Collection: {self._collection_name})")

    def _get_daily_close_values(self, coin_name: str, date_start: str, date_end: str) -> List[PriceData]:
        """일별 종가 데이터 조회 (내부 메서드)"""
        try:
            pipeline = [
                {
                    "$match": {
                        "coin_name": coin_name,
                        "date": {
                            "$gte": date_start,
                            "$lte": date_end
                        }
                    }
                },
                {
                    "$sort": {
                        "date": 1,
                        "price_data.time": 1
                    }
                },
                {
                    "$group": {
                        "_id": "$date",
                        "latestPrice": {"$last": "$price_data"}
                    }
                },
                {
                    "$sort": {"_id": 1}
                },
                {
                    "$project": {
                        "_id": 0,
                        "date": "$_id",
                        "close": "$latestPrice.close",
                        "time": "$latestPrice.time"
                    }
                }
            ]

            results = list(self.collection.aggregate(pipeline))
            return [PriceData(**result) for result in results]
        except Exception as e:
            print(f"[ERROR] Daily close query failed: {e}")
            return []

    def _get_hourly_price_data(self, coin_name: str, pivot_time: int) -> List[PriceHourlyData]:
        """시간별 가격 데이터 조회 (내부 메서드) - ±1시간"""
        try:
            time_start = pivot_time - 3600
            time_end = pivot_time + 3600

            results = self.collection.find({
                "coin_name": coin_name,
                "price_date.time": {
                    "$gte": time_start,
                    "$lte": time_end
                }
            }).sort("price_date.time", 1)

            formatted_results = []
            for doc in results:
                price_data = doc.get("price_date", {})
                formatted_results.append(PriceHourlyData(
                    time=price_data.get("time"),
                    high=price_data.get("high"),
                    low=price_data.get("low"),
                    open=price_data.get("open"),
                    close=price_data.get("close")
                ))

            return formatted_results
        except Exception as e:
            print(f"[ERROR] Hourly price query failed: {e}")
            return []

    # ==================== 통합 메서드 (Public) ====================

    def find_by_range(
        self,
        coin_name: str,
        pivot_date: int,
        range_type: Literal["hour", "day", "week", "month", "year"] = "week",
        direction: Literal["before", "after", "both"] = "before"
    ) -> Union[List[PriceData], List[PriceHourlyData]]:
        """
        통합 가격 조회 메서드

        Args:
            coin_name: 코인 심볼 (BTC, ETH 등)
            pivot_date: 기준 날짜 (epoch timestamp)
            range_type: 조회 범위 - hour, day, week, month, year
            direction: 방향 - before(과거), after(미래), both(양방향)

        Returns:
            - range_type이 "hour"인 경우: List[PriceHourlyData]
            - 그 외: List[PriceData]

        Examples:
            # BTC 7일 전 가격
            find_by_range("BTC", 1727740800, "week", "before")

            # ETH 1개월 양방향
            find_by_range("ETH", 1727740800, "month", "both")
        """
        try:
            # 시간별 데이터 조회 (±1시간)
            if range_type == "hour":
                return self._get_hourly_price_data(coin_name, pivot_date)

            # 일별 데이터 조회
            offset = RANGE_OFFSETS.get(range_type, RANGE_OFFSETS["week"])

            if direction == "before":
                date_start = datetime.fromtimestamp(pivot_date - offset).strftime("%Y-%m-%d")
                date_end = datetime.fromtimestamp(pivot_date).strftime("%Y-%m-%d")
            elif direction == "after":
                date_start = datetime.fromtimestamp(pivot_date).strftime("%Y-%m-%d")
                date_end = datetime.fromtimestamp(pivot_date + offset).strftime("%Y-%m-%d")
            else:  # both
                date_start = datetime.fromtimestamp(pivot_date - offset).strftime("%Y-%m-%d")
                date_end = datetime.fromtimestamp(pivot_date + offset).strftime("%Y-%m-%d")

            return self._get_daily_close_values(coin_name, date_start, date_end)

        except Exception as e:
            print(f"[ERROR] Price query failed: {e}")
            return []


