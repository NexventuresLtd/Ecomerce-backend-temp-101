from fastapi import Depends
from sqlalchemy.orm import Session
from .database import engine, SessionLocal
from typing import Annotated
from models.userModels import  Base as UserBase
from models.Categories import  Base as CategoriesBase
from models.Products import  Base as ProductsBase
from models.cart_wish import Base as CartBase
from models.billing import Base as BillingCard
from models.vlog import Base as VlogBase

UserBase.metadata.create_all(bind=engine) # for users models
CategoriesBase.metadata.create_all(bind=engine) # for categories models
ProductsBase.metadata.create_all(bind=engine) # for products models
CartBase.metadata.create_all(bind=engine) # for Cart models 
BillingCard.metadata.create_all(bind=engine) # for Billing models 
VlogBase.metadata.create_all(bind=engine) # for Billing models 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]