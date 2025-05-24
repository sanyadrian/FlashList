from fastapi import APIRouter, Depends, HTTPException
from app.auth.auth_handler import decode_token
from fastapi.security import OAuth2PasswordBearer
from app.db import get_session
from app.models.user_db import User as DBUser
from app.models.listing_db import Listing as DBListing
from sqlmodel import select
from collections import Counter

router = APIRouter(prefix="/admin", tags=["Admin"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_admin_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if username != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        return username
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/users")
def get_all_users(admin=Depends(get_admin_user)):
    with get_session() as session:
        users = session.exec(select(DBUser)).all()
        return [{"username": u.username, "email": u.email} for u in users]

@router.get("/listings")
def get_all_listings(admin=Depends(get_admin_user)):
    with get_session() as session:
        listings = session.exec(select(DBListing)).all()
        return [{"id": l.id, "title": l.title, "owner": l.owner} for l in listings]

@router.get("/stats")
def get_stats(admin=Depends(get_admin_user)):
    with get_session() as session:
        total_users = session.exec(select(DBUser)).all()
        total_listings = session.exec(select(DBListing)).all()
        category_count = Counter(l.category for l in total_listings)
        return {
            "user_count": len(total_users),
            "listing_count": len(total_listings),
            "top_categories": category_count.most_common(5)
        }
