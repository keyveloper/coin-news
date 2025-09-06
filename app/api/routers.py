"""API 라우터 등록"""
from fastapi import APIRouter
from app.api.v1.endpoint.crawl_router import bloomingbit_router
from app.api.v1.endpoint.batch_router import batch_route
from app.api.v1.endpoint.agent_router import bot_route

# API v1 라우터
api_router = APIRouter(prefix="/api/v1")

# 각 endpoint 라우터 등록
api_router.include_router(bloomingbit_router)
api_router.include_router(batch_route)
api_router.include_router(bot_route)
