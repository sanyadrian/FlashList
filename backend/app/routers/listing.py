from fastapi import APIRouter

router = APIRouter(prefix="/listing", tags=["Listing"])

@router.get("/ping")
def ping():
    return {"status": "Listing route works!"}
