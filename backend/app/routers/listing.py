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

def get_ebay_category_id(category: str) -> str:
    """
    Map our categories to eBay leaf category IDs.
    Returns a valid eBay leaf category ID based on the listing category.
    """
    category_mapping = {
        "Plants": "1",         # Collectibles (very general, should work)
        "Flowers": "1",        # Collectibles (very general, should work)
        "Garden": "1",         # Collectibles (very general, should work)
        "Home": "1",           # Collectibles (very general, should work)
        "Electronics": "293",  # Electronics & Accessories
        "Clothing": "1",       # Collectibles (fallback)
        "Books": "267",        # Books & Magazines
        "Sports": "888",       # Sporting Goods
        "Toys": "220",         # Toys & Hobbies
        "Automotive": "6000",  # Automotive Parts & Accessories
        "Health": "180959",    # Health & Beauty
        "Jewelry": "281",      # Jewelry & Watches
        "Collectibles": "1",   # Collectibles
        "Art": "550",          # Art
        "Music": "176985",     # Musical Instruments & Gear
        "Tools": "631",        # Business & Industrial > Manufacturing & Metalworking > Welding & Soldering Equipment
        "Furniture": "11700",  # Home & Garden > Furniture
        "Kitchen": "20667",    # Home & Garden > Kitchen, Dining & Bar
        "Outdoor": "1",        # Collectibles (fallback for outdoor items)
    }
    
    # Try to find an exact match first
    if category in category_mapping:
        return category_mapping[category]
    
    # Try to find a partial match
    for key, value in category_mapping.items():
        if key.lower() in category.lower() or category.lower() in key.lower():
            return value
    
    # Default fallback - use Collectibles as it's very general and should work
    return "1"  # Collectibles

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

    # Validate required fields
    if not listing.title or len(listing.title.strip()) == 0:
        raise HTTPException(status_code=400, detail="Title is required")
    if not listing.description or len(listing.description.strip()) == 0:
        raise HTTPException(status_code=400, detail="Description is required")
    if not listing.image_filenames or len(listing.image_filenames) == 0:
        raise HTTPException(status_code=400, detail="At least one image is required")
    if not listing.price or listing.price <= 0:
        raise HTTPException(status_code=400, detail="Valid price is required")

    # Convert image filenames to S3 URLs
    image_urls = [f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{filename}" for filename in listing.image_filenames]

    # Generate a unique SKU
    sku = str(uuid.uuid4())

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Content-Language": "en-US"
    }

    # First, create the inventory item
    inventory_item = {
        "sku": sku,
        "product": {
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
                "Country/Region of Manufacture": ["US"]
            },
            "country": "US",
            "title": listing.title
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
        },
        "country": "US"
    }

    # Create inventory item using PUT to the correct URL with SKU
    inventory_url = f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}"
    print(f"[DEBUG] Creating inventory item with data: {json.dumps(inventory_item, indent=2)}")
    print(f"[DEBUG] Headers: {json.dumps(headers, indent=2)}")
    
    # Add retry logic for transient errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.put(inventory_url, json=inventory_item, headers=headers, timeout=30)
            if response.status_code in (200, 201, 204):  # 204 means success with no content
                break
            elif response.status_code == 500 and attempt < max_retries - 1:
                print(f"[DEBUG] eBay API returned 500, retrying... (attempt {attempt + 1}/{max_retries})")
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"[DEBUG] Request failed, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                raise HTTPException(status_code=500, detail=f"Failed to connect to eBay API: {str(e)}")
    
    if response.status_code not in (200, 201, 204):
        print(f"[DEBUG] Failed to create inventory item: {response.text}")
        print(f"[DEBUG] Response headers: {dict(response.headers)}")
        print(f"[DEBUG] Response status: {response.status_code}")
        raise HTTPException(status_code=400, detail=f"Failed to create eBay inventory item: {response.text}")

    # eBay does not return inventoryItemId, use sku
    inventory_item_id = sku

    # Get or create merchant location
    merchant_location = await get_or_create_merchant_location(token)

    if not merchant_location:
        raise HTTPException(
            status_code=400,
            detail="eBay merchant location required. Please visit your eBay Seller Hub to create a location first, then try again. See /listing/ebay/setup-instructions for detailed steps."
        )

    # Update existing location to include postal code if it's the default location
    if merchant_location == "LOCATION_1":
        print("[DEBUG] Updating existing location with postal code...")
        update_location_data = {
            "location": {
                "address": {
                    "country": "US",
                    "city": "New York",
                    "postalCode": "10001"
                }
            },
            "locationTypes": ["WAREHOUSE"],
            "merchantLocationKey": "LOCATION_1",
            "merchantLocationStatus": "ENABLED"
        }
        
        update_url = f"https://api.ebay.com/sell/inventory/v1/location/{merchant_location}"
        response = requests.put(update_url, json=update_location_data, headers=headers)
        print(f"[DEBUG] Location update response status: {response.status_code}")
        print(f"[DEBUG] Location update response: {response.text}")
        
        # If location update fails, we need to handle this properly
        if response.status_code not in (200, 201, 204):
            print("[DEBUG] Location update failed, trying alternative approach...")
            
            # Try to get the current location details first
            try:
                get_location_url = f"https://api.ebay.com/sell/inventory/v1/location/{merchant_location}"
                get_response = requests.get(get_location_url, headers=headers, timeout=30)
                print(f"[DEBUG] Get location response status: {get_response.status_code}")
                print(f"[DEBUG] Get location response: {get_response.text}")
                
                if get_response.status_code == 200:
                    current_location = get_response.json()
                    print(f"[DEBUG] Current location data: {json.dumps(current_location, indent=2)}")
                    
                    # Check if it already has a postal code
                    address = current_location.get("location", {}).get("address", {})
                    if address.get("postalCode"):
                        print(f"[DEBUG] Location already has postal code: {address.get('postalCode')}")
                    else:
                        print("[DEBUG] Creating new location with postal code...")
                        
                        # Check if LOCATION_2 already exists
                        existing_locations = []
                        try:
                            get_all_response = requests.get("https://api.ebay.com/sell/inventory/v1/location", headers=headers, timeout=30)
                            if get_all_response.status_code == 200:
                                existing_locations = get_all_response.json().get("locations", [])
                        except:
                            pass
                        
                        # Find an available location key
                        used_keys = {loc["merchantLocationKey"] for loc in existing_locations}
                        new_location_key = None
                        for i in range(2, 10):  # Try LOCATION_2 through LOCATION_9
                            candidate_key = f"LOCATION_{i}"
                            if candidate_key not in used_keys:
                                new_location_key = candidate_key
                                break
                        
                        if not new_location_key:
                            raise HTTPException(
                                status_code=400,
                                detail="Too many eBay locations exist. Please delete some locations in your eBay Seller Hub first."
                            )
                        
                        new_location_data = {
                            "location": {
                                "address": {
                                    "country": "US",
                                    "city": "New York",
                                    "postalCode": "10001"
                                }
                            },
                            "locationTypes": ["WAREHOUSE"],
                            "merchantLocationKey": new_location_key,
                            "merchantLocationStatus": "ENABLED"
                        }
                        
                        new_location_url = f"https://api.ebay.com/sell/inventory/v1/location/{new_location_key}"
                        new_response = requests.post(new_location_url, json=new_location_data, headers=headers, timeout=30)
                        print(f"[DEBUG] New location creation response status: {new_response.status_code}")
                        print(f"[DEBUG] New location creation response: {new_response.text}")
                        
                        if new_response.status_code in (200, 201, 204):
                            print(f"[DEBUG] New location created successfully: {new_location_key}")
                            merchant_location = new_location_key
                        else:
                            # If we can't create a new location, we need to fail
                            raise HTTPException(
                                status_code=400,
                                detail="Unable to update or create eBay location with valid postal code. Please visit your eBay Seller Hub to create a location with a valid postal code first."
                            )
                else:
                    # If we can't get location details, we need to fail
                    raise HTTPException(
                        status_code=400,
                        detail="Unable to retrieve eBay location details. Please visit your eBay Seller Hub to create a location with a valid postal code first."
                    )
            except Exception as e:
                print(f"[DEBUG] Exception during location handling: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Unable to configure eBay location properly. Please visit your eBay Seller Hub to create a location with a valid postal code first."
                )

    # Create offer
    offer = {
        "sku": sku,
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "availableQuantity": 1,
        "categoryId": get_ebay_category_id(listing.category),
        "itemTitle": listing.title,
        "listingDescription": listing.description,
        "listingDuration": "DAYS_7",
        "listingPolicies": {
            "fulfillmentPolicyId": token_record.fulfillment_policy_id,
            "paymentPolicyId": token_record.payment_policy_id,
            "returnPolicyId": token_record.return_policy_id
        },
        "pricingSummary": {
            "price": {
                "currency": "USD",
                "value": str(listing.price)
            }
        },
        "quantityLimitPerBuyer": 1,
        "includeCatalogProductDetails": True,
        "merchantLocationKey": merchant_location
    }
    
    print(f"[DEBUG] Using merchant location: {merchant_location}")

    # Create offer
    offer_url = "https://api.ebay.com/sell/inventory/v1/offer"
    print(f"[DEBUG] Creating offer with data: {json.dumps(offer, indent=2)}")
    
    # Add retry logic for offer creation
    for attempt in range(max_retries):
        try:
            response = requests.post(offer_url, json=offer, headers=headers, timeout=30)
            if response.status_code == 201:
                break
            elif response.status_code == 500 and attempt < max_retries - 1:
                print(f"[DEBUG] eBay offer API returned 500, retrying... (attempt {attempt + 1}/{max_retries})")
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"[DEBUG] Offer request failed, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                raise HTTPException(status_code=500, detail=f"Failed to connect to eBay API: {str(e)}")
    
    if response.status_code != 201:
        print(f"[DEBUG] Failed to create offer: {response.text}")
        print(f"[DEBUG] Response status: {response.status_code}")
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

async def get_or_create_merchant_location(token: str) -> str:
    """
    Get the first available merchant location from eBay, or create a basic one if none exists.
    Returns the location key or None if creation fails.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # First, try to get existing locations
    try:
        response = requests.get(
            "https://api.ebay.com/sell/inventory/v1/location",
            headers=headers,
            timeout=30
        )
        
        print(f"[DEBUG] Location fetch response status: {response.status_code}")
        print(f"[DEBUG] Location fetch response: {response.text}")
        
        if response.status_code == 200:
            locations = response.json().get("locations", [])
            print(f"[DEBUG] Found {len(locations)} existing locations")
            if locations:
                # Look for a location that already has a postal code
                for location in locations:
                    address = location.get("location", {}).get("address", {})
                    if address.get("postalCode"):
                        location_key = location["merchantLocationKey"]
                        print(f"[DEBUG] Using existing location with postal code: {location_key}")
                        return location_key
                
                # If no location has postal code, use the first one and try to update it
                location_key = locations[0]["merchantLocationKey"]
                print(f"[DEBUG] Using existing location without postal code: {location_key}")
                return location_key
    except Exception as e:
        print(f"[DEBUG] Exception fetching locations: {e}")
    
    # Try to create a basic location if none exists
    print("[DEBUG] No locations found, attempting to create basic location...")
    
    # Try different location data structures
    location_attempts = [
        {
            "location": {
                "address": {
                    "country": "US",
                    "city": "New York",
                    "postalCode": "10001"
                }
            },
            "locationTypes": [
                "WAREHOUSE"
            ],
            "merchantLocationKey": "LOCATION_1",
            "merchantLocationStatus": "ENABLED"
        }
    ]
    
    for i, location_data in enumerate(location_attempts):
        print(f"[DEBUG] Trying location creation attempt {i+1} with data: {json.dumps(location_data, indent=2)}")
        
        try:
            # Use the merchantLocationKey in the URL path
            location_url = f"https://api.ebay.com/sell/inventory/v1/location/{location_data['merchantLocationKey']}"
            response = requests.post(
                location_url,
                json=location_data,
                headers=headers,
                timeout=30
            )
            
            print(f"[DEBUG] Location creation attempt {i+1} response status: {response.status_code}")
            print(f"[DEBUG] Location creation attempt {i+1} response: {response.text}")
            
            if response.status_code in (200, 201, 204):  # 204 means success with no content
                print(f"[DEBUG] Location created successfully on attempt {i+1}")
                return location_data['merchantLocationKey']
        except Exception as e:
            print(f"[DEBUG] Exception on location creation attempt {i+1}: {e}")
    
    print("[DEBUG] All location creation attempts failed")
    print("[DEBUG] This user needs to create a location in their eBay Seller Hub first")
    return None
