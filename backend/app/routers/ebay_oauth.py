from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from app.auth.auth_handler import decode_token
from fastapi.security import OAuth2PasswordBearer
from app.db import get_session
from app.models.ebay_oauth_db import EbayOAuth
from sqlmodel import Session, select
import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
import uuid

load_dotenv()

router = APIRouter(prefix="/ebay/oauth", tags=["eBay OAuth"])

# eBay OAuth Configuration
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EBAY_REDIRECT_URI = os.getenv("EBAY_REDIRECT_URI")
EBAY_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SCOPE = "https://api.ebay.com/oauth/api_scope/sell.inventory"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/start")
async def start_oauth(user: str = Depends(get_current_user)):
    """
    Start the eBay OAuth flow by redirecting the user to eBay's login page.
    """
    if not all([EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REDIRECT_URI]):
        raise HTTPException(status_code=500, detail="eBay OAuth configuration is incomplete")

    state = str(uuid.uuid4())
    
    with get_session() as session:
        pass

    auth_url = (
        f"{EBAY_AUTH_URL}?"
        f"client_id={EBAY_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={EBAY_REDIRECT_URI}&"
        f"scope={EBAY_SCOPE}&"
        f"state={state}"
    )

    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    user: str = Depends(get_current_user)
):
    """
    Handle the callback from eBay OAuth flow.
    Exchange the authorization code for access and refresh tokens.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": EBAY_REDIRECT_URI
    }

    response = requests.post(
        EBAY_TOKEN_URL,
        data=token_data,
        auth=(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get access token: {response.text}"
        )

    token_response = response.json()
    
    expires_at = datetime.utcnow() + timedelta(seconds=token_response["expires_in"])

    with get_session() as session:
        existing_token = session.query(EbayOAuth).filter(EbayOAuth.user_id == user).first()
        
        if existing_token:
            existing_token.access_token = token_response["access_token"]
            existing_token.refresh_token = token_response["refresh_token"]
            existing_token.expires_at = expires_at
            existing_token.updated_at = datetime.utcnow()
            session.add(existing_token)
        else:
            new_token = EbayOAuth(
                id=str(uuid.uuid4()),
                user_id=user,
                access_token=token_response["access_token"],
                refresh_token=token_response["refresh_token"],
                expires_at=expires_at
            )
            session.add(new_token)
        
        session.commit()

    return {"message": "Successfully connected to eBay"}

@router.post("/refresh")
async def refresh_token(user: str = Depends(get_current_user)):
    """
    Refresh the eBay access token using the refresh token.
    """
    with get_session() as session:
        token_record = session.query(EbayOAuth).filter(EbayOAuth.user_id == user).first()
        
        if not token_record:
            raise HTTPException(status_code=404, detail="No eBay tokens found for user")

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": token_record.refresh_token
        }

        response = requests.post(
            EBAY_TOKEN_URL,
            data=token_data,
            auth=(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to refresh token: {response.text}"
            )

        token_response = response.json()
        
        token_record.access_token = token_response["access_token"]
        token_record.expires_at = datetime.utcnow() + timedelta(seconds=token_response["expires_in"])
        token_record.updated_at = datetime.utcnow()
        
        session.add(token_record)
        session.commit()

        return {"message": "Token refreshed successfully"}

@router.get("/status")
async def check_ebay_auth(user: str = Depends(get_current_user)):
    """
    Check if the user has eBay authentication.
    """
    with get_session() as session:
        token_record = session.query(EbayOAuth).filter(EbayOAuth.user_id == user).first()
        
        if not token_record:
            raise HTTPException(status_code=404, detail="No eBay tokens found for user")
            
        # Check if token is expired
        if token_record.expires_at < datetime.utcnow():
            # Try to refresh the token
            try:
                token_data = {
                    "grant_type": "refresh_token",
                    "refresh_token": token_record.refresh_token
                }

                response = requests.post(
                    EBAY_TOKEN_URL,
                    data=token_data,
                    auth=(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET),
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if response.status_code != 200:
                    raise HTTPException(status_code=401, detail="eBay token expired and refresh failed")

                token_response = response.json()
                
                # Update tokens in database
                token_record.access_token = token_response["access_token"]
                token_record.expires_at = datetime.utcnow() + timedelta(seconds=token_response["expires_in"])
                token_record.updated_at = datetime.utcnow()
                
                session.add(token_record)
                session.commit()
            except Exception as e:
                raise HTTPException(status_code=401, detail="eBay token expired and refresh failed")

        return {"status": "authenticated"} 