"""
Configuration module
"""
from .chroma_config import get_chroma_client, ChromaDBClient, COLLECTION_NAME

__all__ = ['get_chroma_client', 'ChromaDBClient', 'COLLECTION_NAME']