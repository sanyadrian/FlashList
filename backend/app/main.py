from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import listing, image_upload, listing_ai, pricing, auth_router, admin
from app.db import create_db_and_tables

app = FastAPI()
create_db_and_tables()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listing.router)
app.include_router(image_upload.router)
app.include_router(listing_ai.router)
app.include_router(pricing.router)
app.include_router(auth_router.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "FlashList backend is live"}
