from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import listing, image_upload, listing_ai, pricing

app = FastAPI()

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

@app.get("/")
def root():
    return {"message": "FlashList backend is live"}
