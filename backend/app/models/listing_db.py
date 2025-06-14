from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

class Listing(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    owner: str
    title: str
    description: str
    category: str
    tags: str 
    image_filenames: str
    marketplaces: str
    brand: Optional[str] = None
    marketplace_status: str = Field(default="{}")
    price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ebay_item_id: Optional[str] = Field(default=None, index=True)
