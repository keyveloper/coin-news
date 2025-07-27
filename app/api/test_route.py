from fastapi import APIRouter
from app.models.schemas import MyCustomResponse, MyCustomRequest
from app.services.scraper import coin_news_scrape
from fastapi import Query

test_router = APIRouter(prefix="/test", tags=["test"])


@test_router.get("", response_model=MyCustomResponse)
def get_test(name: str = Query(
    ..., #required parameter
    min_length=2,
    max_length=10,
)):
    return MyCustomResponse(message=f"{name} successful")


@test_router.get("/body", response_model=MyCustomResponse)
def read_body(request: MyCustomRequest):
    return MyCustomResponse(message=f"hello!! {request.name}, {request.age}")

@test_router.get("/simple")
def get_simple():
    coin_news_scrape()
    return {"id": 1, "name": "J"}