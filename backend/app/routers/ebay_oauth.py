from fastapi import APIRouter, HTTPException, Depends, Request, Query
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
import base64
import json

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
async def start_oauth(token: str = Query(None)):
    """
    Start the eBay OAuth flow by redirecting the user to eBay's login page.
    Accepts a 'token' query parameter for authentication (for SafariView compatibility).
    """
    user = None
    if token:
        try:
            payload = decode_token(token)
            user = payload["sub"]
            print(f"[DEBUG] /ebay/oauth/start: user from token: {user}")
        except Exception as e:
            print(f"[DEBUG] /ebay/oauth/start: invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token in query param")
    else:
        print("[DEBUG] /ebay/oauth/start: no token provided")
        raise HTTPException(status_code=401, detail="No token provided")

    if not all([EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REDIRECT_URI]):
        raise HTTPException(status_code=500, detail="eBay OAuth configuration is incomplete")

    # Encode user info in state
    state_data = {"user": user, "nonce": str(uuid.uuid4())}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    auth_url = (
        f"{EBAY_AUTH_URL}?"
        f"client_id={EBAY_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={EBAY_REDIRECT_URI}&"  # This is the RuName, not a URL
        f"scope={EBAY_SCOPE}&"
        f"state={state}"
    )

    print(f"[DEBUG] Redirecting to eBay OAuth URL: {auth_url}")
    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str
):
    """
    Handle the callback from eBay OAuth flow.
    Exchange the authorization code for access and refresh tokens.
    """
    print("[DEBUG] /ebay/oauth/callback called")
    print(f"[DEBUG] code: {code}")
    print(f"[DEBUG] state: {state}")
    if not code:
        print("[DEBUG] No authorization code provided")
        raise HTTPException(status_code=400, detail="Authorization code is missing")

    # Decode user from state
    try:
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        user = state_data["user"]
        print(f"[DEBUG] user from state: {user}")
    except Exception as e:
        print(f"[DEBUG] Failed to decode state: {e}")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": EBAY_REDIRECT_URI  # This is the RuName, not a URL
    }

    response = requests.post(
        EBAY_TOKEN_URL,
        data=token_data,
        auth=(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    print(f"[DEBUG] Token exchange response status: {response.status_code}")
    print(f"[DEBUG] Token exchange response body: {response.text}")

    if response.status_code != 200:
        print("[DEBUG] Failed to get access token from eBay")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get access token: {response.text}"
        )

    token_response = response.json()
    print(f"[DEBUG] token_response: {token_response}")
    expires_at = datetime.utcnow() + timedelta(seconds=token_response["expires_in"])

    with get_session() as session:
        existing_token = session.query(EbayOAuth).filter(EbayOAuth.user_id == user).first()
        if existing_token:
            print("[DEBUG] Updating existing eBay token record")
            existing_token.access_token = token_response["access_token"]
            existing_token.refresh_token = token_response["refresh_token"]
            existing_token.expires_at = expires_at
            existing_token.updated_at = datetime.utcnow()
            session.add(existing_token)
        else:
            print("[DEBUG] Creating new eBay token record")
            new_token = EbayOAuth(
                id=str(uuid.uuid4()),
                user_id=user,
                access_token=token_response["access_token"],
                refresh_token=token_response["refresh_token"],
                expires_at=expires_at
            )
            session.add(new_token)
        session.commit()
        print("[DEBUG] eBay token record saved to database")

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
    print("[DEBUG] /ebay/oauth/status called")
    print(f"[DEBUG] Authenticated user: {user}")
    with get_session() as session:
        token_record = session.query(EbayOAuth).filter(EbayOAuth.user_id == user).first()
        print(f"[DEBUG] eBay token record for user {user}: {token_record}")
        if not token_record:
            print("[DEBUG] No eBay tokens found for user")
            raise HTTPException(status_code=404, detail="No eBay tokens found for user")
        print(f"[DEBUG] Token expires at: {token_record.expires_at}, now: {datetime.utcnow()}")
        # Check if token is expired
        if token_record.expires_at < datetime.utcnow():
            print("[DEBUG] eBay token expired, attempting refresh...")
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
                print(f"[DEBUG] Refresh response status: {response.status_code}, body: {response.text}")
                if response.status_code != 200:
                    print("[DEBUG] eBay token expired and refresh failed")
                    raise HTTPException(status_code=401, detail="eBay token expired and refresh failed")
                token_response = response.json()
                # Update tokens in database
                token_record.access_token = token_response["access_token"]
                token_record.expires_at = datetime.utcnow() + timedelta(seconds=token_response["expires_in"])
                token_record.updated_at = datetime.utcnow()
                session.add(token_record)
                session.commit()
                print("[DEBUG] eBay token refreshed successfully")
            except Exception as e:
                print(f"[DEBUG] Exception during token refresh: {e}")
                raise HTTPException(status_code=401, detail="eBay token expired and refresh failed")
        print("[DEBUG] eBay authentication status: authenticated")
        return {"status": "authenticated"} 