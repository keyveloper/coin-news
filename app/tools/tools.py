from typing import Dict
from langchain.tools import tool
from app.agent.query_analyzer_agent import QueryAnalyzerService


@tool
def analyze_query(query: str) -> Dict:
    return QueryAnalyzerService().analyze_query(query)
