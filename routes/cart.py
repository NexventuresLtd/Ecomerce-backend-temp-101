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
    if product.instock < quantity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The Quantity entered is high")
        

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
        if product.instock < cart_item.quantity + quantity :
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The Quantity entered is high")
        
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
    View all items in the logged-in user's active cart with detailed product information.
    """
    user_id = user["user_id"]

    cart = db.query(Cart).filter(Cart.user_id == user_id, Cart.is_active == True).first()
    if not cart:
        return {
            "cart_id": None,
            "items": [],
            "total_items": 0,
            "total_price": 0.0,
            "message": "No active cart found"
        }

    # Get cart items with product details
    cart_items = (
        db.query(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .filter(CartItem.cart_id == cart.id)
        .all()
    )

    items = []
    total_items = 0
    total_price = 0.0

    for cart_item, product in cart_items:
        item_total = cart_item.quantity * cart_item.price_at_time
        items.append({
            "cart_item_id": cart_item.id,
            "product_id": product.id,
            "product_name": product.title,
            "delivery_fee":product.delivery_fee,
            "product_image": product.images,
            "current_price": product.price,
            "price_at_time": cart_item.price_at_time,
            "quantity": cart_item.quantity,
            "item_total": item_total,
            "in_stock": product.instock,
            "max_available": min(product.instock, product.instock)  # You might want to adjust this
        })
        total_items += cart_item.quantity
        total_price += item_total

    return {
        "cart_id": cart.id,
        "user_id": user_id,
        "items": items,
        "total_items": total_items,
        "total_price": total_price,
        "cart_status": cart.is_active,
        "created_at": cart.created_at
    }

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
    Admin: View all carts with their items - optimized version
    """
    # Get all carts with user information
    carts = db.query(Cart).all()
    
    # Get all cart items in one query
    all_cart_items = db.query(CartItem).all()
    
    # Get all products in one query
    product_ids = {item.product_id for item in all_cart_items}
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_dict = {product.id: product for product in products}
    
    # Get all users in one query
    user_ids = {cart.user_id for cart in carts}
    users = db.query(Users).filter(Users.id.in_(user_ids)).all()
    user_dict = {user.id: user for user in users}
    
    result = []
    for cart in carts:
        # Filter items for this cart
        cart_items = [item for item in all_cart_items if item.cart_id == cart.id]
        
        user_info = user_dict.get(cart.user_id)
        
        cart_data = {
            "id": cart.id,
            "user_id": cart.user_id,
            "fname": user_info.fname,
            "lname": user_info.lname,
            "phone":user_info.phone,
            "email": user_info.email if user_info else None,
            "is_active": cart.is_active,
            "created_at": cart.created_at,
            "items": [],
            "total_items": 0,
            "total_price": 0
        }
        
        # Add items to the cart
        for item in cart_items:
            product = product_dict.get(item.product_id)
            
            item_data = {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": product.title if product else "Product Not Found",
                "product_price": product.price if product else 0,
                "quantity": item.quantity,
                "price_at_time": item.price_at_time,
                "created_at": item.created_at,
                "total_item_price": item.quantity * item.price_at_time
            }
            cart_data["items"].append(item_data)
            cart_data["total_items"] += item.quantity
            cart_data["total_price"] += item.quantity * item.price_at_time
        
        result.append(cart_data)
    
    return {"carts": result}


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
