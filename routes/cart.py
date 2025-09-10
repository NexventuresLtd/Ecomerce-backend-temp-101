from fastapi import APIRouter, HTTPException, status
from db.connection import db_dependency
from db.VerifyToken import user_dependency
from models.cart_wish import Cart, CartItem
from models.Products import Product
from models.userModels import Users

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post("/add")
async def add_to_cart(product_id: int, quantity: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Add a product to the logged-in user's active cart.
    """
    user_id = user["user_id"]

    db_user = db.query(Users).filter(Users.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    # Ensure the user has an active cart
    cart = db.query(Cart).filter(Cart.user_id == user_id, Cart.is_active == True).first()
    if not cart:
        cart = Cart(user_id=user_id, is_active=True)
        db.add(cart)
        db.commit()
        db.refresh(cart)

    # Check if product already exists in cart
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.product_id == product_id
    ).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product_id,
            quantity=quantity,
            price_at_time=product.price
        )
        db.add(cart_item)

    db.commit()
    return {"message": "Product added to cart successfully"}


@router.get("/my-cart")
async def view_cart(db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    View all items in the logged-in user's active cart.
    """
    user_id = user["user_id"]

    cart = db.query(Cart).filter(Cart.user_id == user_id, Cart.is_active == True).first()
    if not cart:
        return {"cart": []}

    items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    return {"cart_id": cart.id, "items": items}


@router.put("/update/{cart_item_id}")
async def update_cart_item(cart_item_id: int, quantity: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Update the quantity of a cart item (only if it belongs to the logged-in user).
    """
    user_id = user["user_id"]

    cart_item = (
        db.query(CartItem)
        .join(Cart, Cart.id == CartItem.cart_id)
        .filter(CartItem.id == cart_item_id, Cart.user_id == user_id, Cart.is_active == True)
        .first()
    )
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    cart_item.quantity = quantity
    db.commit()
    return {"message": "Cart item updated successfully"}


@router.delete("/delete/{cart_item_id}")
async def delete_cart_item(cart_item_id: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Delete a product from the logged-in user's cart.
    """
    user_id = user["user_id"]

    cart_item = (
        db.query(CartItem)
        .join(Cart, Cart.id == CartItem.cart_id)
        .filter(CartItem.id == cart_item_id, Cart.user_id == user_id, Cart.is_active == True)
        .first()
    )
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    db.delete(cart_item)
    db.commit()
    return {"message": "Cart item deleted successfully"}


# ----------- ADMIN ENDPOINTS -----------

@router.get("/all")
async def get_all_carts(db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Admin: View all carts
    """
    # you may want to check user["role"] here to enforce admin-only
    carts = db.query(Cart).all()
    return {"carts": carts}


@router.put("/toggle/{cart_id}")
async def toggle_cart_status(cart_id: int, is_active: bool, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Admin: Activate/Deactivate a cart
    """
    # you may want to check user["role"] here to enforce admin-only
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    cart.is_active = is_active
    db.commit()
    return {"message": f"Cart status updated to {'Active' if is_active else 'Inactive'}"}
