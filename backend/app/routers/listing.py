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
from typing import Optional, Dict, Any
from app.utils.s3 import BUCKET_NAME, REGION
import os
from dotenv import load_dotenv
import hashlib
import requests
from app.routers.ebay_oauth import get_ebay_token
from app.models.ebay_oauth_db import EbayOAuth

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

class EbayNotificationData(BaseModel):
    username: str
    userId: str
    eiasToken: str

class EbayNotification(BaseModel):
    notificationId: str
    eventDate: str
    publishDate: str
    publishAttemptCount: int
    data: EbayNotificationData

class EbayNotificationRequest(BaseModel):
    metadata: Dict[str, Any]
    notification: EbayNotification

async def create_ebay_listing(listing: Listing, user: str):
    """
    Create a new listing in both our database and eBay.
    """
    # Get eBay token
    token = await get_ebay_token(user)
    if not token:
        raise HTTPException(status_code=401, detail="eBay authentication required")

    # Get policy IDs from database
    with get_session() as session:
        token_record = session.query(EbayOAuth).filter(EbayOAuth.user_id == user).first()
        if not token_record:
            raise HTTPException(status_code=401, detail="eBay authentication required")
        
        # Check if we have all required policies
        if not all([token_record.fulfillment_policy_id, token_record.payment_policy_id, token_record.return_policy_id]):
            missing_policies = []
            if not token_record.fulfillment_policy_id:
                missing_policies.append("fulfillment")
            if not token_record.payment_policy_id:
                missing_policies.append("payment")
            if not token_record.return_policy_id:
                missing_policies.append("return")
            raise HTTPException(
                status_code=400,
                detail=f"Missing required eBay business policies: {', '.join(missing_policies)}. Please create these policies in your eBay Seller Hub first."
            )

    # Convert image filenames to S3 URLs
    image_urls = [f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{filename}" for filename in listing.image_filenames]

    # Generate a unique SKU
    sku = str(uuid.uuid4())

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
    }

    # First, create the inventory item
    inventory_item = {
        "sku": sku,
        "product": {
            "title": listing.title,
            "description": listing.description,
            "imageUrls": image_urls,
            "productIdentifiers": {
                "productId": {
                    "value": sku,
                    "type": "SKU"
                }
            },
            "brand": listing.brand if listing.brand else "Generic",
            "mpn": sku,  # Manufacturer Part Number
            "aspects": {
                "Brand": [listing.brand if listing.brand else "Generic"],
                "Condition": ["New"],
                "Type": ["Fixed Price"],
                "Plant Type": ["Succulent"],
                "Plant Form": ["Live Plant"],
                "Growing Zone": ["4-9"],
                "Sun Exposure": ["Full Sun"],
                "Water Needs": ["Low"]
            }
        },
        "condition": "NEW",
        "packageWeightAndSize": {
            "dimensions": {
                "height": 1,
                "length": 1,
                "width": 1,
                "unit": "INCH"
            },
            "weight": {
                "value": 1,
                "unit": "POUND"
            }
        },
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 1
            }
        }
    }

    # Create inventory item using PUT to the correct URL with SKU
    inventory_url = f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}"
    print(f"[DEBUG] Creating inventory item with data: {json.dumps(inventory_item, indent=2)}")
    print(f"[DEBUG] Headers: {json.dumps(headers, indent=2)}")
    
    response = requests.put(inventory_url, json=inventory_item, headers=headers)
    if response.status_code not in (200, 201):
        print(f"[DEBUG] Failed to create inventory item: {response.text}")
        print(f"[DEBUG] Response headers: {dict(response.headers)}")
        raise HTTPException(status_code=400, detail=f"Failed to create eBay inventory item: {response.text}")

    # eBay does not return inventoryItemId, use sku
    inventory_item_id = sku

    # Create offer
    offer = {
        "sku": sku,
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "availableQuantity": 1,
        "categoryId": "177009",  # Plants & Seeds category
        "listingDescription": listing.description,
        "listingPolicies": {
            "fulfillmentPolicyId": token_record.fulfillment_policy_id,
            "paymentPolicyId": token_record.payment_policy_id,
            "returnPolicyId": token_record.return_policy_id
        },
        "pricingSummary": {
            "price": {
                "value": str(listing.price),
                "currency": "USD"
            }
        },
        "merchantLocationKey": "LOCATION_1",
        "inventoryItemId": inventory_item_id,
        "aspects": {
            "Brand": [listing.brand if listing.brand else "Generic"],
            "Condition": ["New"],
            "Type": ["Fixed Price"],
            "Plant Type": ["Succulent"],
            "Plant Form": ["Live Plant"],
            "Growing Zone": ["4-9"],
            "Sun Exposure": ["Full Sun"],
            "Water Needs": ["Low"]
        }
    }

    # Create offer
    offer_url = "https://api.ebay.com/sell/inventory/v1/offer"
    print(f"[DEBUG] Creating offer with data: {json.dumps(offer, indent=2)}")
    response = requests.post(offer_url, json=offer, headers=headers)
    if response.status_code != 201:
        print(f"[DEBUG] Failed to create offer: {response.text}")
        raise HTTPException(status_code=400, detail=f"Failed to create eBay offer: {response.text}")

    offer_id = response.json()["offerId"]

    # Publish offer
    publish_url = f"https://api.ebay.com/sell/inventory/v1/offer/{offer_id}/publish"
    response = requests.post(publish_url, headers=headers)
    if response.status_code != 200:
        print(f"[DEBUG] Failed to publish offer: {response.text}")
        raise HTTPException(status_code=400, detail=f"Failed to publish eBay offer: {response.text}")

    return offer_id

@router.post("/create")
async def create_listing(data: Listing, user=Depends(get_current_user)):
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

        # If eBay is selected, create the listing on eBay
        if "eBay" in data.marketplaces:
            try:
                ebay_item_id = await create_ebay_listing(data, user)
                listing.ebay_item_id = ebay_item_id
                marketplace_status["eBay"] = "posted"
                listing.marketplace_status = json.dumps(marketplace_status)
                session.add(listing)
                session.commit()
            except Exception as e:
                marketplace_status["eBay"] = "failed"
                listing.marketplace_status = json.dumps(marketplace_status)
                session.add(listing)
                session.commit()
                print(f"[DEBUG] Failed to create eBay listing: {str(e)}")

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
    request: Request,
    x_ebay_signature: str = Header(..., alias="X-EBAY-SIGNATURE")
):
    """
    Handle deletion notifications from eBay.
    This endpoint is called by eBay when a marketplace account is deleted.
    """
    body = await request.body()
    print("=== eBay Deletion Notification Debug Info ===")
    print(f"Raw Request Body: {body}")
    print(f"Headers: {request.headers}")
    print(f"X-EBAY-SIGNATURE: {x_ebay_signature}")
    print("===========================================")

    try:
        data = await request.json()
        print(f"Parsed JSON data: {data}")
        
        notification_request = EbayNotificationRequest(**data)
        
        user_id = notification_request.notification.data.userId
        
        with get_session() as session:
            listings = session.query(DBListing).filter(DBListing.owner == user_id).all()
            
            for listing in listings:
                if "eBay" in listing.marketplaces.split(","):
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
                "message": "Account deletion processed successfully",
                "userId": user_id,
                "affected_listings": len(listings)
            }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.get("/ebay/deletion-notification")
async def handle_ebay_challenge(request: Request, challenge_code: str = Query(...)):
    """
    Handle eBay's challenge request for marketplace account deletion notification endpoint validation.
    """
    expected_token = os.getenv("EBAY_VERIFICATION_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="Verification token not configured")
    
    endpoint = str(request.url).split("?")[0].replace("http://", "https://")
    
    print("=== eBay Challenge Debug Info ===")
    print(f"Challenge Code: {challenge_code}")
    print(f"Verification Token: {expected_token}")
    print(f"Endpoint URL: {endpoint}")
    print(f"Full Request URL: {request.url}")
    print(f"Base URL: {request.base_url}")
    print(f"Headers: {request.headers}")
    
    m = hashlib.sha256()
    m.update(challenge_code.encode('utf-8'))
    m.update(expected_token.encode('utf-8'))
    m.update(endpoint.encode('utf-8'))
    challenge_response = m.hexdigest()
    
    print(f"Challenge Response: {challenge_response}")
    print("===============================")
    
    return JSONResponse(
        content={"challengeResponse": challenge_response},
        headers={"Content-Type": "application/json"}
    )
