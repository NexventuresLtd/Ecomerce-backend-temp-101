from fastapi import APIRouter, HTTPException, status
from db.connection import db_dependency
from db.VerifyToken import user_dependency
from models.cart_wish import Wishlist, WishlistItem, Cart, CartItem
from models.Products import Product
from models.userModels import Users
from typing import List, Dict, Any

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.post("/add")
async def add_to_wishlist(
    product_id: int,
    quantity: int,
    db: db_dependency,
    user: user_dependency,
    delivery: str,
    color: List[Dict[str, Any]] = []
):
    if isinstance(user, HTTPException):
        raise user

    """
    Add a product to the logged-in user's active wishlist.
    """
    user_id = user["user_id"]

    db_user = db.query(Users).filter(Users.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
    if product.instock < quantity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The Quantity entered is high")

    # Ensure the user has an active wishlist
    wishlist = db.query(Wishlist).filter(Wishlist.user_id == user_id, Wishlist.is_active == True).first()
    if not wishlist:
        wishlist = Wishlist(user_id=user_id, is_active=True)
        db.add(wishlist)
        db.commit()
        db.refresh(wishlist)

    # Check if product already exists in wishlist
    wishlist_item = db.query(WishlistItem).filter(
        WishlistItem.wishlist_id == wishlist.id, WishlistItem.product_id == product_id
    ).first()

    if wishlist_item:
        if product.instock < wishlist_item.quantity + quantity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The Quantity entered is high")

        wishlist_item.quantity += quantity
        wishlist_item.color = color
        wishlist_item.delivery = delivery
    else:
        wishlist_item = WishlistItem(
            color=color,
            wishlist_id=wishlist.id,
            product_id=product_id,
            quantity=quantity,
            price_at_time=product.price,
            delivery=delivery
        )
        db.add(wishlist_item)

    db.commit()
    return {"message": "Product added to wishlist successfully"}


@router.get("/my-wishlist")
async def view_wishlist(db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    View all items in the logged-in user's active wishlist with detailed product information.
    """
    user_id = user["user_id"]

    wishlist = db.query(Wishlist).filter(Wishlist.user_id == user_id, Wishlist.is_active == True).first()
    if not wishlist:
        return {
            "wishlist_id": None,
            "items": [],
            "total_items": 0,
            "total_price": 0.0,
            "message": "No active wishlist found"
        }

    # Get wishlist items with product details
    wishlist_items = (
        db.query(WishlistItem, Product)
        .join(Product, WishlistItem.product_id == Product.id)
        .filter(WishlistItem.wishlist_id == wishlist.id)
        .all()
    )

    items = []
    total_items = 0
    total_price = 0.0

    for wishlist_item, product in wishlist_items:
        item_total = wishlist_item.quantity * wishlist_item.price_at_time
        items.append({
            "wishlist_item_id": wishlist_item.id,
            "product_id": product.id,
            "product_name": product.title,
            "delivery_fee": product.delivery_fee,
            "product_image": product.images,
            "current_price": product.price,
            "price_at_time": wishlist_item.price_at_time,
            "quantity": wishlist_item.quantity,
            "wishlist_color": wishlist_item.color,
            "product_color": product.colors,
            "delivery": wishlist_item.delivery,
            "item_total": item_total,
            "in_stock": product.instock,
            "max_available": min(product.instock, product.instock)
        })
        total_items += wishlist_item.quantity
        total_price += item_total

    return {
        "wishlist_id": wishlist.id,
        "user_id": user_id,
        "items": items,
        "total_items": total_items,
        "total_price": total_price,
        "wishlist_status": wishlist.is_active,
        "created_at": wishlist.created_at
    }


@router.put("/update/{wishlist_item_id}")
async def update_wishlist_item(
    wishlist_item_id: int,
    quantity: int,
    db: db_dependency,
    user: user_dependency,
    delivery: str,
    color: List[Dict[str, Any]] = []
):
    if isinstance(user, HTTPException):
        raise user

    """
    Update the quantity of a wishlist item (only if it belongs to the logged-in user).
    """
    user_id = user["user_id"]

    wishlist_item = (
        db.query(WishlistItem)
        .join(Wishlist, Wishlist.id == WishlistItem.wishlist_id)
        .filter(WishlistItem.id == wishlist_item_id, Wishlist.user_id == user_id, Wishlist.is_active == True)
        .first()
    )
    if not wishlist_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    wishlist_item.quantity = quantity
    wishlist_item.color = color
    wishlist_item.delivery = delivery
    db.commit()
    return {"message": "Wishlist item updated successfully"}


@router.delete("/delete/{wishlist_item_id}")
async def delete_wishlist_item(wishlist_item_id: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Delete a product from the logged-in user's wishlist.
    """
    user_id = user["user_id"]

    wishlist_item = (
        db.query(WishlistItem)
        .join(Wishlist, Wishlist.id == WishlistItem.wishlist_id)
        .filter(WishlistItem.id == wishlist_item_id, Wishlist.user_id == user_id, Wishlist.is_active == True)
        .first()
    )
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
    Admin: View all wishlists with their items - optimized version
    """
    wishlists = db.query(Wishlist).all()
    all_wishlist_items = db.query(WishlistItem).all()

    # Get all products
    product_ids = {item.product_id for item in all_wishlist_items}
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_dict = {product.id: product for product in products}

    # Get all users
    user_ids = {wishlist.user_id for wishlist in wishlists}
    users = db.query(Users).filter(Users.id.in_(user_ids)).all()
    user_dict = {user.id: user for user in users}

    result = []
    for wishlist in wishlists:
        wishlist_items = [item for item in all_wishlist_items if item.wishlist_id == wishlist.id]

        user_info = user_dict.get(wishlist.user_id)

        wishlist_data = {
            "id": wishlist.id,
            "user_id": wishlist.user_id,
            "fname": user_info.fname,
            "lname": user_info.lname,
            "phone": user_info.phone,
            "email": user_info.email if user_info else None,
            "is_active": wishlist.is_active,
            "created_at": wishlist.created_at,
            "items": [],
            "total_items": 0,
            "total_price": 0
        }

        for item in wishlist_items:
            product = product_dict.get(item.product_id)

            item_data = {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": product.title if product else "Product Not Found",
                "product_price": product.price if product else 0,
                "quantity": item.quantity,
                "wishlist_color": item.color,
                "product_color": product.colors,
                "delivery": item.delivery,
                "price_at_time": item.price_at_time,
                "created_at": item.created_at,
                "total_item_price": item.quantity * item.price_at_time
            }
            wishlist_data["items"].append(item_data)
            wishlist_data["total_items"] += item.quantity
            wishlist_data["total_price"] += item.quantity * item.price_at_time

        result.append(wishlist_data)

    return {"wishlists": result}


@router.put("/toggle/{wishlist_id}")
async def toggle_wishlist_status(wishlist_id: int, is_active: bool, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Admin: Activate/Deactivate a wishlist
    """
    wishlist = db.query(Wishlist).filter(Wishlist.id == wishlist_id).first()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    wishlist.is_active = is_active
    db.commit()
    return {"message": f"Wishlist status updated to {'Active' if is_active else 'Inactive'}"}

@router.post("/move-to-cart/{wishlist_item_id}")
async def move_to_cart(
    wishlist_item_id: int,
    db: db_dependency,
    user: user_dependency
):
    if isinstance(user, HTTPException):
        raise user

    user_id = user["user_id"]

    # Get the wishlist item
    wishlist_item = (
        db.query(WishlistItem)
        .join(Wishlist, Wishlist.id == WishlistItem.wishlist_id)
        .filter(WishlistItem.id == wishlist_item_id, Wishlist.user_id == user_id, Wishlist.is_active == True)
        .first()
    )
    if not wishlist_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    # Get the product to validate stock
    product = db.query(Product).filter(Product.id == wishlist_item.product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    if product.instock < wishlist_item.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock available")

    # Ensure the user has an active cart
    cart = db.query(Cart).filter(Cart.user_id == user_id, Cart.is_active == True).first()
    if not cart:
        cart = Cart(user_id=user_id, is_active=True)
        db.add(cart)
        db.commit()
        db.refresh(cart)

    # Check if the product is already in the cart
    cart_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.product_id == wishlist_item.product_id)
        .first()
    )

    if cart_item:
        # Update existing cart item
        if product.instock < cart_item.quantity + wishlist_item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock available")
        cart_item.quantity += wishlist_item.quantity
        cart_item.color = wishlist_item.color
        cart_item.delivery = wishlist_item.delivery
    else:
        # Create new cart item
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=wishlist_item.product_id,
            quantity=wishlist_item.quantity,
            price_at_time=wishlist_item.price_at_time,
            color=wishlist_item.color,
            delivery=wishlist_item.delivery,
        )
        db.add(cart_item)

    # Remove the item from wishlist
    db.delete(wishlist_item)

    db.commit()
    return {"message": "Product moved from wishlist to cart successfully"}
