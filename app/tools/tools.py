from typing import Dict
from langchain.tools import tool
from app.services.query_analyzer_service import QueryAnalyzerService


@tool
def analyze_query(query: str) -> Dict:
    return QueryAnalyzerService().analyze_query(query)
