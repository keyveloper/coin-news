"""API 라우터 등록"""
from fastapi import APIRouter
from app.api.v1.endpoint.coinness_router import coinness_router
from app.api.v1.endpoint.test_router import test_router
from app.api.v1.endpoint.bloomingbit_router import bloomingbit_router
from app.api.v1.endpoint.naver_news_router import naver_news_router
from app.api.v1.endpoint.batch_router import batch_route

# API v1 라우터
api_router = APIRouter(prefix="/api/v1")

# 각 endpoint 라우터 등록
api_router.include_router(test_router)
api_router.include_router(coinness_router)
api_router.include_router(bloomingbit_router)
api_router.include_router(naver_news_router)
api_router.include_router(batch_route)