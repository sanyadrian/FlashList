from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class EbayOAuth(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    access_token: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    fulfillment_policy_id: Optional[str] = None
    payment_policy_id: Optional[str] = None
    return_policy_id: Optional[str] = None 