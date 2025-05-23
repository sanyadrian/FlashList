from fastapi import APIRouter
import uuid
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.auth.auth_handler import decode_token
from fastapi import HTTPException
from app.models.listing import Listing
from app.db import get_session
from app.models.listing_db import Listing as DBListing
from sqlmodel import Session
import uuid


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

router = APIRouter(prefix="/listing", tags=["Listing"])

@router.post("/create")
def create_listing(data: Listing, user=Depends(get_current_user)):
    with get_session() as session:
        listing = DBListing(
            id=str(uuid.uuid4()),
            owner=user,
            title=data.title,
            description=data.description,
            category=data.category,
            tags=",".join(data.tags),
            image_filenames=",".join(data.image_filenames),
            price=data.price
        )
        session.add(listing)
        session.commit()
        return {"id": listing.id, "message": "Listing created"}


@router.get("/my")
def get_my_listings(user=Depends(get_current_user)):
    with get_session() as session:
        listings = session.query(DBListing).filter(DBListing.owner == user).all()
        return [
            {
                "id": l.id,
                "title": l.title,
                "description": l.description,
                "category": l.category,
                "tags": l.tags.split(","),
                "image_filenames": l.image_filenames.split(","),
                "price": l.price,
                "created_at": l.created_at
            }
            for l in listings
        ]

