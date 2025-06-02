from sqlmodel import SQLModel, create_engine, Session
import os

# DATABASE_URL = "sqlite:///flashlist.db"
DATABASE_URL = os.getenv("DATABASE_URL")

# engine = create_engine(DATABASE_URL, echo=False)
engine = create_engine(DATABASE_URL, echo=False, connect_args={})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
