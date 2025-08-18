from fastapi import Depends
from sqlalchemy.orm import Session
from .database import engine, SessionLocal
from typing import Annotated
from models.userModels import  Base

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]