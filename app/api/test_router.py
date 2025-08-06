from fastapi import APIRouter, Query

from app.schemas.schemas import MyCustomResponse, MyCustomRequest

test_router = APIRouter(prefix="/coinness", tags=["coinness"])


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
