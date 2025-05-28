from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app.auth.auth_handler import hash_password, verify_password, create_access_token, decode_token
from app.models.auth import User, Token
from app.db import get_session
from app.models.user_db import User as DBUser
from sqlmodel import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/auth", tags=["Authentication"])

fake_users_db = {
    "testuser": {
        "email": "test@example.com",
        "hashed_password": hash_password("testpass")
    }
}

@router.post("/register")
def register(user: User):
    with get_session() as session:
        existing = session.get(DBUser, user.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already registered")
        email_exists = session.exec(
            select(DBUser).where(DBUser.email == user.email)
        ).first()
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already registered")

        db_user = DBUser(
            username=user.username,
            email=user.email,
            hashed_password=hash_password(user.password)
        )
        session.add(db_user)
        session.commit()

    return {"message": "User registered successfully"}




@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password

    with get_session() as session:
        db_user = session.get(DBUser, username)
        if not db_user or not verify_password(password, db_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def get_current_user_info(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        with get_session() as session:
            user = session.get(DBUser, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return {"username": user.username, "email": user.email}
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.put("/update")
def update_user_profile(data: User, token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        with get_session() as session:
            user = session.get(DBUser, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.username = data.username
            user.email = data.email
            user.hashed_password = hash_password(data.password)
            session.add(user)
            session.commit()
            return {"message": "Profile updated successfully"}
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

