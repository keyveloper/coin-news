"""Naver News API Request/Response 스키마"""
from typing import List, Optional
from pydantic import BaseModel, Field


class NaverNewsRequest(BaseModel):
    """Naver News API 요청 파라미터"""
    query: str = Field(..., description="검색어")
    display: int = Field(default=10, ge=1, le=100, description="검색 결과 출력 건수 (최대 100)")
    start: int = Field(default=1, ge=1, description="검색 시작 위치")
    sort: str = Field(default="sim", pattern="^(sim|date)$", description="정렬 옵션 (sim: 정확도순, date: 날짜순)")


class NaverNewsItem(BaseModel):
    """Naver News API 뉴스 아이템"""
    title: str = Field(..., description="뉴스 제목 (HTML 태그 포함)")
    originallink: str = Field(..., description="뉴스 원문 링크")
    link: str = Field(..., description="네이버 뉴스 링크")
    description: str = Field(..., description="뉴스 내용 요약 (HTML 태그 포함)")
    pubDate: str = Field(..., description="뉴스 게시 날짜 (RFC 1123 형식)")


class NaverNewsResponse(BaseModel):
    """Naver News API 응답"""
    lastBuildDate: str = Field(..., description="검색 결과를 생성한 시간")
    total: int = Field(..., description="총 검색 결과 개수")
    start: int = Field(..., description="검색 시작 위치")
    display: int = Field(..., description="한 번에 표시할 검색 결과 개수")
    items: List[NaverNewsItem] = Field(default_factory=list, description="뉴스 검색 결과 목록")


class NaverNewsAPIResponse(BaseModel):
    """Naver News API 전체 응답 (루트)"""
    lastBuildDate: str
    total: int
    start: int
    display: int
    items: List[NaverNewsItem]

class NaverNewsMetadataAndRawContent(BaseModel):
    lastBuildDate: str
    title: str
    originalLink: str
    author: str
    media: str
    rawContent: str

