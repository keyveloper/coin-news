from pydantic import BaseModel, Field

class MyCustomResponse(BaseModel):
    """
    Response model for testing
    """
    message: str = Field(..., description="Status message")

class MyCustomRequest(BaseModel):
    name: str
    age: int