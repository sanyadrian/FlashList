from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.auth.auth_handler import decode_token
from fastapi import HTTPException
from app.models.listing import Listing


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

router = APIRouter(prefix="/listing", tags=["Listing"])

mock_listing_db = {}

    
@router.post("/create")
async def create_listing(data: Listing, user=Depends(get_current_user)):
    listing_id = str(uuid.uuid4())
    mock_listing_db[listing_id] = {**data.dict(), "owner": user}
    return {"id": listing_id, "message": "Listing created"}


@router.get("/my")
async def get_my_listings(user=Depends(get_current_user)):
    user_listings = [
        {"id": lid, **listing}
        for lid, listing in mock_listing_db.items()
        if listing.get("owner") == user
    ]
    return user_listings
