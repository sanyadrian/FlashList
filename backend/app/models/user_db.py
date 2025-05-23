from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    username: str = Field(primary_key=True)
    email: str
    hashed_password: str
