from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.auth_handler import hash_password, verify_password, create_access_token
from app.models.auth import User, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

fake_users_db = {
    "testuser": {
        "email": "test@example.com",
        "hashed_password": hash_password("testpass")
    }
}

@router.post("/register")
def register(user: User):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already registered")

    fake_users_db[user.username] = {
        "email": user.email,
        "hashed_password": hash_password(user.password)
    }

    return {"message": "User registered successfully"}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    user_data = fake_users_db.get(username)

    if not user_data or not verify_password(password, user_data["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}
