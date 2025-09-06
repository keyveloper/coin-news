"""Vector Tools for Embedding Generation"""
import logging
from typing import List
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

# Global embedding model (singleton)
_embedding_model = None


def _get_embedding_model():
    """Get or initialize embedding model"""
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = OpenAIEmbeddings(
                model="text-embedding-3-small"
            )
            logger.info("Embedding model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    return _embedding_model


@tool
def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector from text for semantic search using OpenI.

    Args:
        text: Text to convert to embedding vector

    Returns:
        List of floats representing the embedding vector (1536 dimensions for text-embedding-3-small)
    """
    try:
        model = _get_embedding_model()
        # OpenAIEmbeddings uses embed_query method, not encode
        embedding = model.embed_query(text)
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


@tool
def generate_search_query_from_context(
    coin_name: str,
    intent_type: str,
    analysis_instructions: str
) -> str:
    """
    Generate semantic search query from context.

    Combines coin name, intent type, and extracts keywords from analysis instructions
    to create an effective search query.

    Args:
        coin_name: Cryptocurrency symbol (e.g., "BTC", "ETH")
        intent_type: Type of intent (market_trend, price_reason, news_summary)
        analysis_instructions: Instructions containing keywords and context

    Returns:
        Optimized search query string
    """
    # Intent-specific keywords
    intent_keywords = {
        "market_trend": ["trend", "pattern", "movement", "direction"],
        "price_reason": ["catalyst", "reason", "factor", "impact", "cause"],
        "news_summary": ["development", "update", "event", "announcement"]
    }

    # Extract keywords from analysis_instructions
    import re
    # Common crypto/finance keywords to look for
    keyword_patterns = [
        r'\b(regulat\w+|adoption|upgrade|partnership|merger|acquisition)\b',
        r'\b(surge|decline|volatility|stability|rally|crash)\b',
        r'\b(institutional|retail|whale|trader|investor)\b',
        r'\b(DeFi|NFT|Layer\s*\d+|protocol|blockchain)\b',
        r'\b(bullish|bearish|neutral|sentiment)\b'
    ]

    extracted_keywords = []
    for pattern in keyword_patterns:
        matches = re.findall(pattern, analysis_instructions, re.IGNORECASE)
        extracted_keywords.extend([m if isinstance(m, str) else m[0] for m in matches])

    # Combine components
    query_parts = [coin_name]

    # Add intent-specific keywords
    if intent_type in intent_keywords:
        query_parts.extend(intent_keywords[intent_type][:2])  # Top 2 keywords

    # Add extracted keywords (limit to 5)
    if extracted_keywords:
        query_parts.extend(list(set(extracted_keywords))[:5])

    query = " ".join(query_parts)
    logger.info(f"Generated search query: {query}")

    return query


@tool
def embed_search_query(
    coin_name: str,
    intent_type: str,
    analysis_instructions: str
) -> List[float]:
    """
    Generate embedding for semantic news search from context.

    This is a convenience tool that combines query generation and embedding.

    Args:
        coin_name: Cryptocurrency symbol (e.g., "BTC", "ETH")
        intent_type: Type of intent (market_trend, price_reason, news_summary)
        analysis_instructions: Instructions containing keywords and context

    Returns:
        Embedding vector for semantic search
    """
    # Generate query
    query = generate_search_query_from_context.func(
        coin_name=coin_name,
        intent_type=intent_type,
        analysis_instructions=analysis_instructions
    )

    # Generate embedding
    embedding = generate_embedding.func(query)
    print("embedding:", embedding)

    return embedding
