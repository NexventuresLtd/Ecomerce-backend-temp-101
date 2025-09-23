# routes/dashboard.py
from fastapi import APIRouter, HTTPException
from sqlalchemy import func

from db.connection import db_dependency
from models.userModels import Users, LoginLogs
from models.Products import Product
from models.Categories import SubCategory,ProductCategory,MainCategory
from models.cart_wish import Cart, Wishlist
from models.billing import Billing
  # adjust import if different

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary(db: db_dependency):
    try:
        # --- Users ---
        total_users = db.query(func.count(Users.id)).scalar()
        active_users = db.query(func.count(Users.id)).filter(Users.is_active == True).scalar()
        verified_users = db.query(func.count(Users.id)).filter(Users.is_verified == True).scalar()

        # --- Products ---
        total_products = db.query(func.count(Product.id)).scalar()
        active_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()
        featured_products = db.query(func.count(Product.id)).filter(Product.is_featured == True).scalar()

        # --- Categories ---
        main_categories = db.query(func.count(MainCategory.id)).scalar()
        sub_categories = db.query(func.count(SubCategory.id)).scalar()
        product_categories = db.query(func.count(ProductCategory.id)).scalar()

        # --- Carts ---
        total_carts = db.query(func.count(Cart.id)).scalar()
        active_carts = db.query(func.count(Cart.id)).filter(Cart.is_active == True).scalar()
        inactive_carts = db.query(func.count(Cart.id)).filter(Cart.is_active == False).scalar()

        # --- Wishlists ---
        total_wishlists = db.query(func.count(Wishlist.id)).scalar()
        active_wishlists = db.query(func.count(Wishlist.id)).filter(Wishlist.is_active == True).scalar()
        inactive_wishlists = db.query(func.count(Wishlist.id)).filter(Wishlist.is_active == False).scalar()

        # --- Billing ---
        total_billings = db.query(func.count(Billing.id)).scalar()

        # --- Logs ---
        total_logins = db.query(func.count(LoginLogs.id)).scalar()
        active_devices = db.query(func.count(LoginLogs.id)).filter(LoginLogs.device_active == True).scalar()

        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "verified": verified_users,
            },
            "products": {
                "total": total_products,
                "active": active_products,
                "featured": featured_products,
            },
            "categories": {
                "main": main_categories,
                "sub": sub_categories,
                "product": product_categories,
            },
            "carts": {
                "total": total_carts,
                "active": active_carts,
                "inactive": inactive_carts,
            },
            "wishlists": {
                "total": total_wishlists,
                "active": active_wishlists,
                "inactive": inactive_wishlists,
            },
            "billings": total_billings,
            "logs": {
                "total_logins": total_logins,
                "active_devices": active_devices,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
