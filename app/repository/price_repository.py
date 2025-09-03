"""
MongoDB 가격 데이터 저장소
"""
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pymongo.database import Database
from pymongo.collection import Collection
from app.config.mongodb_config import get_mongodb_client


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
        if not hasattr(self, '_initialized'):
            self._initialized = True

            # 데이터베이스 및 컬렉션 이름 설정
            self._database_name = "local"
            self._collection_name = "price.log"

            # MongoDB 클라이언트 연결
            self.mongo_client = get_mongodb_client()
            self.db: Database = self.mongo_client.get_database(self._database_name)
            self.collection: Collection = self.db[self._collection_name]

            print(f"✅ PriceRepository 초기화 완료 (DB: {self._database_name}, Collection: {self._collection_name})")

    def _get_daily_close_values(self, coin_name: str, date_start: str, date_end: str) -> List[Dict]:
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
            return results
        except Exception as e:
            print(f"❌ 날짜별 close 값 조회 실패: {e}")
            return []

    def find_by_coin_name_with_hour_range(
        self,
        coin_name: str,
        spot_time: int
    ) -> List[Dict]:
        try:
            # 1시간 = 3600초
            time_start = spot_time - 3600
            time_end = spot_time + 3600

            # 각 시간별 데이터 조회
            results = self.collection.find({
                "coin_name": coin_name,
                "price_date.time": {
                    "$gte": time_start,
                    "$lte": time_end
                }
            }).sort("price_date.time", 1)

            # 필요한 필드만 추출
            formatted_results = []
            for doc in results:
                price_data = doc.get("price_date", {})
                formatted_results.append({
                    "time": price_data.get("time"),
                    "high": price_data.get("high"),
                    "low": price_data.get("low"),
                    "open": price_data.get("open"),
                    "close": price_data.get("close")
                })

            return formatted_results
        except Exception as e:
            print(f"❌ 시간별 가격 조회 실패: {e}")
            return []

    def find_by_coin_name_with_oneday(
        self,
        coin_name: str,
        pivot_date: int
    ) -> List[Dict]:
        try:
            # pivot_date가 00:00:00인지 확인
            pivot_dt = datetime.fromtimestamp(pivot_date)
            if pivot_dt.hour != 0 or pivot_dt.minute != 0 or pivot_dt.second != 0:
                raise ValueError(
                    f"pivot_date는 00:00:00이어야 합니다. "
                    f"현재: {pivot_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            # epoch time을 날짜 문자열로 변환
            date_str = pivot_dt.strftime("%Y-%m-%d")

            results = self._get_daily_close_values(coin_name, date_str, date_str)
            return results
        except ValueError:
            raise
        except Exception as e:
            print(f"❌ 일별 가격 조회 실패: {e}")
            return []

    def find_by_coin_name_with_week_before(
        self,
        coin_name: str,
        spot_date: int
    ) -> List[Dict]:
        try:
            date_start = datetime.fromtimestamp(spot_date - (7 * 24 * 60 * 60)).strftime("%Y-%m-%d")
            date_end = datetime.fromtimestamp(spot_date).strftime("%Y-%m-%d")

            results = self._get_daily_close_values(coin_name, date_start, date_end)
            return results
        except Exception as e:
            print(f"❌ 주간 가격 조회 실패: {e}")
            return []

    def find_by_coin_name_with_week_after(
        self,
        coin_name: str,
        spot_date: int
    ) -> List[Dict]:
        try:
            date_start = datetime.fromtimestamp(spot_date).strftime("%Y-%m-%d")
            date_end = datetime.fromtimestamp(spot_date + (7 * 24 * 60 * 60)).strftime("%Y-%m-%d")

            results = self._get_daily_close_values(coin_name, date_start, date_end)
            return results
        except Exception as e:
            print(f"❌ 주간 가격 조회 실패: {e}")
            return []

    def find_by_coin_name_with_month_before(
        self,
        coin_name: str,
        spot_date: int
    ) -> List[Dict]:
        try:
            date_start = datetime.fromtimestamp(spot_date - (30 * 24 * 60 * 60)).strftime("%Y-%m-%d")
            date_end = datetime.fromtimestamp(spot_date).strftime("%Y-%m-%d")

            results = self._get_daily_close_values(coin_name, date_start, date_end)
            return results
        except Exception as e:
            print(f"❌ 월간 가격 조회 실패: {e}")
            return []

    def find_by_coin_name_with_month_after(
        self,
        coin_name: str,
        spot_date: int
    ) -> List[Dict]:
        try:
            date_start = datetime.fromtimestamp(spot_date).strftime("%Y-%m-%d")
            date_end = datetime.fromtimestamp(spot_date + (30 * 24 * 60 * 60)).strftime("%Y-%m-%d")

            results = self._get_daily_close_values(coin_name, date_start, date_end)
            return results
        except Exception as e:
            print(f"❌ 월간 가격 조회 실패: {e}")
            return []

    def find_by_coin_name_with_year(
        self,
        coin_name: str,
        spot_date: int
    ) -> List[Dict]:
        try:
            date_start = datetime.fromtimestamp(spot_date - (365 * 24 * 60 * 60)).strftime("%Y-%m-%d")
            date_end = datetime.fromtimestamp(spot_date).strftime("%Y-%m-%d")

            results = self._get_daily_close_values(coin_name, date_start, date_end)
            return results
        except Exception as e:
            print(f"❌ 연간 가격 조회 실패: {e}")
            return []

    def find_by_coin(
        self,
        coin_name: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        try:
            # 전체 기간 조회 (매우 넓은 범위)
            date_start = "2000-01-01"
            date_end = datetime.now().strftime("%Y-%m-%d")

            results = self._get_daily_close_values(coin_name, date_start, date_end)

            if limit:
                results = results[:limit]

            return results
        except Exception as e:
            print(f"❌ 코인 데이터 조회 실패: {e}")
            return []


