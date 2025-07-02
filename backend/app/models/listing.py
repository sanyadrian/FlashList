from pydantic import BaseModel
from typing import List, Dict, Optional

class Listing(BaseModel):
    title: str
    description: str
    category: str
    tags: List[str]
    price: float
    image_filenames: List[str]
    marketplaces: List[str]
    brand: Optional[str] = None
    condition: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_postal_code: Optional[str] = None
    marketplace_status: Dict[str, str] = {}