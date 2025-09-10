from fastapi import APIRouter, Depends, HTTPException, status
from db.connection import db_dependency
from models.cart_wish import Wishlist
from models.Products import Product
from db.VerifyToken import user_dependency  

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.post("/add")
async def add_to_wishlist(product_id: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Add a product to the user's wishlist.
    """
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    # Prevent duplicate (UniqueConstraint handles at DB level too)
    existing = db.query(Wishlist).filter(
        Wishlist.user_id == user["user_id"],
        Wishlist.product_id == product_id
    ).first()

    if existing:
        return {"message": "Product already in wishlist"}

    wishlist_entry = Wishlist(user_id=user["user_id"], product_id=product_id)
    db.add(wishlist_entry)
    db.commit()

    return {"message": "Product added to wishlist successfully"}


@router.get("/my-wishlist")
async def view_wishlist(db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    View all items in the user's wishlist.
    """
    wishlist_items = db.query(Wishlist).filter(Wishlist.user_id == user["user_id"]).all()
    return {"wishlist": wishlist_items}


@router.delete("/delete/{wishlist_id}")
async def delete_wishlist_item(wishlist_id: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Remove an item from the wishlist.
    """
    wishlist_item = db.query(Wishlist).filter(
        Wishlist.id == wishlist_id,
        Wishlist.user_id == user["user_id"]  # make sure user only deletes their own
    ).first()

    if not wishlist_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    db.delete(wishlist_item)
    db.commit()
    return {"message": "Wishlist item deleted successfully"}


# ----------- ADMIN ENDPOINTS -----------

@router.get("/all")
async def get_all_wishlists(db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Admin: View all wishlist entries.
    """
    wishlists = db.query(Wishlist).all()
    return {"wishlists": wishlists}