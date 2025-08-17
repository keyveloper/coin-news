from pydantic import BaseModel, Field

class GeneralMetadata(BaseModel):
    title: str
    link: str
    authors: str
    language: str
    description: str
    published_date: str

class GeneralMetadatWithRaw(BaseModel):
    page_content: str
    metadata: GeneralMetadata

