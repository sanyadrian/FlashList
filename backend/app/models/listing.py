from pydantic import BaseModel
from typing import List

class Listing(BaseModel):
    title: str
    description: str
    category: str
    tags: List[str]
    price: float
    image_filenames: List[str]
