from fastapi import APIRouter
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/listing", tags=["Listing"])

mock_listing_db = {}

class Listing(BaseModel):
    title: str
    description: str
    category: str
    tags: list[str]
    price: float
    image_filename: str

@router.post("/create")
async def create_listing(data: Listing):
    listing_id = str(uuid.uuid4())
    mock_listing_db[listing_id] = data.dict()
    return {"id": listing_id, "message": "Listing created successfully"}
