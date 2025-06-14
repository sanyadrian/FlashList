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
    marketplace_status: Dict[str, str] = {}