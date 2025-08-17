from pydantic import BaseModel, Field

class CoinReaderMetadata(BaseModel):
    title: str
    link: str
    authors: str
    language: str
    description: str
    published_date: str

class CoinReaderMetadatWithRaw(BaseModel):
    page_content: str
    metadata: CoinReaderMetadata
