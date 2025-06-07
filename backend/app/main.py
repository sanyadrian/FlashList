from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, listing, ebay_oauth, image_upload, listing_ai, pricing, auth_router, admin
from app.db import create_db_and_tables

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(listing.router)
app.include_router(ebay_oauth.router)
app.include_router(image_upload.router)
app.include_router(listing_ai.router)
app.include_router(pricing.router)
app.include_router(auth_router.router)
app.include_router(admin.router)

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()

@app.get("/")
def root():
    return {"message": "FlashList backend is live"}
