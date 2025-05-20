from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import listing

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listing.router)

@app.get("/")
def root():
    return {"message": "FlashList backend is live"}
