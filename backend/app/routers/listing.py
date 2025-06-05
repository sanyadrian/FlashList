from fastapi import APIRouter
import uuid
from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from app.auth.auth_handler import decode_token
from fastapi import HTTPException, Header
from app.models.listing import Listing
from app.db import get_session
from app.models.listing_db import Listing as DBListing
from sqlmodel import Session, select
import uuid
import json
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.utils.s3 import BUCKET_NAME, REGION
import os
from dotenv import load_dotenv
import hashlib

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

router = APIRouter(prefix="/listing", tags=["Listing"])

class EbayDeletionRequest(BaseModel):
    ebay_item_id: str
    listing_id: Optional[str] = None  # Optional since we'll primarily use ebay_item_id

@router.post("/create")
def create_listing(data: Listing, user=Depends(get_current_user)):
    if not data.marketplaces or len(data.marketplaces) == 0:
        raise HTTPException(status_code=400, detail="At least one marketplace must be selected")
    
    # Initialize marketplace statuses
    marketplace_status = {marketplace: "pending" for marketplace in data.marketplaces}
    
    with get_session() as session:
        listing = DBListing(
            id=str(uuid.uuid4()),
            owner=user,
            title=data.title,
            description=data.description,
            category=data.category,
            tags=",".join(data.tags),
            image_filenames=",".join(data.image_filenames),
            price=data.price,
            marketplaces=",".join(data.marketplaces),
            marketplace_status=json.dumps(marketplace_status)
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
                "created_at": str(l.created_at),
                "owner": l.owner,
                "marketplaces": l.marketplaces.split(","),
                "marketplace_status": json.loads(l.marketplace_status)
            }
            for l in listings
        ]


@router.get("/{listing_id}")
def get_listing(listing_id: str):
    with get_session() as session:
        listing = session.get(DBListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        return {
            "id": listing.id,
            "title": listing.title,
            "description": listing.description,
            "category": listing.category,
            "tags": listing.tags.split(","),
            "image_filenames": listing.image_filenames.split(","),
            "price": listing.price,
            "owner": listing.owner,
            "created_at": listing.created_at,
            "marketplaces": listing.marketplaces.split(","),
            "marketplace_status": json.loads(listing.marketplace_status)
        }


@router.put("/{listing_id}")
def update_listing(listing_id: str, data: Listing, user=Depends(get_current_user)):
    with get_session() as session:
        listing = session.get(DBListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.owner != user:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Update fields
        listing.title = data.title
        listing.description = data.description
        listing.category = data.category
        listing.tags = ",".join(data.tags)
        listing.image_filenames = ",".join(data.image_filenames)
        listing.price = data.price
        listing.marketplaces = ",".join(data.marketplaces)

        session.add(listing)
        session.commit()
        return {"message": "Listing updated"}


@router.delete("/{listing_id}")
def delete_listing(listing_id: str, user=Depends(get_current_user)):
    with get_session() as session:
        listing = session.get(DBListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.owner != user:
            raise HTTPException(status_code=403, detail="Not authorized")

        session.delete(listing)
        session.commit()
        return {"message": "Listing deleted"}


@router.get("/public/{listing_id}", response_class=HTMLResponse)
def get_public_listing(listing_id: str):
    with get_session() as session:
        listing = session.get(DBListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
            
        image_url = ""
        if listing.image_filenames:
            first_image = listing.image_filenames.split(",")[0]
            image_url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{first_image}"
            
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{listing.title}</title>
            <meta property="og:title" content="{listing.title}" />
            <meta property="og:description" content="{listing.description}" />
            <meta property="og:image" content="{image_url}" />
            <meta property="og:url" content="http://localhost:8000/listing/public/{listing_id}" />
            <meta property="og:type" content="website" />
            <meta property="og:site_name" content="FlashList" />
        </head>
        <body>
            <h1>{listing.title}</h1>
            <p>{listing.description}</p>
            <p>Price: ${listing.price}</p>
            <p>Category: {listing.category}</p>
        </body>
        </html>
        """
        return html_content

@router.post("/ebay/deletion-notification")
async def handle_ebay_deletion(
    data: EbayDeletionRequest,
    x_ebay_signature: str = Header(..., alias="X-EBAY-SIGNATURE")
):
    """
    Handle deletion notifications from eBay.
    This endpoint is called by eBay when a listing needs to be deleted.
    """
    expected_token = os.getenv("EBAY_VERIFICATION_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="Verification token not configured")
    
    if x_ebay_signature != expected_token:
        raise HTTPException(status_code=401, detail="Invalid verification token")

    with get_session() as session:
        statement = select(DBListing).where(DBListing.ebay_item_id == data.ebay_item_id)
        listing = session.exec(statement).first()
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found for the given eBay item ID")
        
        if "eBay" not in listing.marketplaces.split(","):
            raise HTTPException(status_code=400, detail="Listing is not associated with eBay")
        
        marketplace_status = json.loads(listing.marketplace_status)
        marketplace_status["eBay"] = "deleted"
        listing.marketplace_status = json.dumps(marketplace_status)
        
        if len(listing.marketplaces.split(",")) == 1:
            session.delete(listing)
        else:
            marketplaces = listing.marketplaces.split(",")
            marketplaces.remove("eBay")
            listing.marketplaces = ",".join(marketplaces)
            session.add(listing)
        
        session.commit()
        
        return {
            "status": "success",
            "message": "Deletion processed successfully",
            "ebay_item_id": data.ebay_item_id,
            "listing_id": listing.id
        }

@router.get("/ebay/deletion-notification")
async def handle_ebay_challenge(request: Request, challenge_code: str = Query(...)):
    """
    Handle eBay's challenge request for marketplace account deletion notification endpoint validation.
    """
    expected_token = os.getenv("EBAY_VERIFICATION_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="Verification token not configured")
    
    # Get the full endpoint URL from the request, ensuring it's the base URL without query parameters
    endpoint = str(request.base_url) + "listing/ebay/deletion-notification"
    
    # Log the values for debugging
    print(f"Challenge Code: {challenge_code}")
    print(f"Verification Token: {expected_token}")
    print(f"Endpoint URL: {endpoint}")
    
    # Create the hash as per eBay's requirements
    # Order: challengeCode + verificationToken + endpoint
    m = hashlib.sha256()
    m.update(challenge_code.encode('utf-8'))
    m.update(expected_token.encode('utf-8'))
    m.update(endpoint.encode('utf-8'))
    challenge_response = m.hexdigest()
    
    print(f"Challenge Response: {challenge_response}")
    
    # Return the response in the required format
    return JSONResponse(
        content={"challengeResponse": challenge_response},
        headers={"Content-Type": "application/json"}
    )
