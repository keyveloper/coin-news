from fastapi import APIRouter, Depends

from app.services.query_analyzer_service import QueryAnalyzerService

query_router = APIRouter(prefix="/query", tags=["query"])

@query_router.get("/analyzed")
def query_to_json(
        query: str,
        service: QueryAnalyzerService = Depends(QueryAnalyzerService),
):
    return service.analyze_query(query)
