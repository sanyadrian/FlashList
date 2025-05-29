from pydantic import BaseModel
from typing import List, Dict

class Listing(BaseModel):
    title: str
    description: str
    category: str
    tags: List[str]
    price: float
    image_filenames: List[str]
    marketplaces: List[str]
    marketplace_status: Dict[str, str] = {}