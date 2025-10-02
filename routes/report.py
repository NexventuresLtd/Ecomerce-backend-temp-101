from fastapi import APIRouter, HTTPException
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import Optional

from db.connection import db_dependency
from models.userModels import Users, LoginLogs
from models.Products import Product
from models.Categories import SubCategory, ProductCategory, MainCategory
from models.cart_wish import Cart, Wishlist, CartItem
from models.billing import Billing # keep billing
# Removed: from models.orders import Order, OrderItem

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


@router.get("/comprehensive-report")
async def get_comprehensive_report(
    db: db_dependency,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_details: bool = True
):
    """
    Generate a comprehensive report with detailed information across all entities
    (without orders)
    """
    try:
        # Date filtering
        date_filter = []
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            date_filter.append(func.date(Users.created_at) >= start_dt.date())
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            date_filter.append(func.date(Users.created_at) <= end_dt.date())

        date_condition = and_(*date_filter) if date_filter else True

        # --- USERS DETAILED REPORT ---
        users_query = db.query(Users)
        if date_filter:
            users_query = users_query.filter(date_condition)
        
        users_data = users_query.order_by(desc(Users.created_at)).all()
        
        users_report = []
        for user in users_data:
            user_carts = db.query(func.count(Cart.id)).filter(Cart.user_id == user.id).scalar() or 0
            user_wishlists = db.query(func.count(Wishlist.id)).filter(Wishlist.user_id == user.id).scalar() or 0
            user_billings = db.query(func.count(Billing.id)).filter(Billing.user_id == user.id).scalar() or 0
            
            users_report.append({
                "id": user.id,
                "email": user.email,
                "first_name": user.fname,
                "last_name": user.lname,
                "phone": user.phone,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "cart_count": user_carts,
                "wishlist_count": user_wishlists,
                "billing_count": user_billings
            })

        # --- PRODUCTS DETAILED REPORT ---
        products_data = db.query(Product).order_by(desc(Product.created_at)).all()
        products_report = []
        for product in products_data:
            cart_items_count = db.query(func.count(CartItem.id)).filter(
                CartItem.product_id == product.id
            ).scalar() or 0
            
            products_report.append({
                "id": product.id,
                "name": product.title,
                "price": float(product.price) if product.price else 0,
                "stock_quantity": product.instock,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
                "category_id": product.category_id,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                "cart_appearances": cart_items_count
            })

        # --- CARTS DETAILED REPORT ---
        carts_query = db.query(Cart)
        if date_filter:
            carts_query = carts_query.filter(date_condition)
            
        carts_data = carts_query.order_by(desc(Cart.created_at)).all()
        carts_report = []
        for cart in carts_data:
            cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
            total_items = sum(item.quantity for item in cart_items)
            total_value = sum(float(item.price_at_time or 0) * item.quantity for item in cart_items)
            
            user = db.query(Users).filter(Users.id == cart.user_id).first()
            
            carts_report.append({
                "id": cart.id,
                "user_id": cart.user_id,
                "user_name": f"{user.fname} {user.lname}" if user else "Unknown",
                "user_email": user.email if user else "Unknown",
                "is_active": cart.is_active,
                "total_items": total_items,
                "total_value": total_value,
                "created_at": cart.created_at.isoformat() if cart.created_at else None,
                "updated_at": cart.updated_at.isoformat() if cart.updated_at else None,
                "items_count": len(cart_items),
                "items": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "price_at_time": float(item.price_at_time) if item.price_at_time else 0,
                        "total_item_price": float(item.total_item_price) if item.total_item_price else 0
                    } for item in cart_items
                ] if include_details else []
            })

        # --- WISHLISTS DETAILED REPORT ---
        wishlists_data = db.query(Wishlist).order_by(desc(Wishlist.created_at)).all()
        wishlists_report = []
        for wishlist in wishlists_data:
            user = db.query(Users).filter(Users.id == wishlist.user_id).first()
            
            wishlists_report.append({
                "id": wishlist.id,
                "user_id": wishlist.user_id,
                "user_name": f"{user.fname} {user.lname}" if user else "Unknown",
                "user_email": user.email if user else "Unknown",
                "is_active": wishlist.is_active,
                "created_at": wishlist.created_at.isoformat() if wishlist.created_at else None
            })

        # --- BILLINGS DETAILED REPORT ---
        billings_data = db.query(Billing).order_by(desc(Billing.created_at)).all()
        billings_report = []
        for billing in billings_data:

            user = db.query(Users).filter(Users.id == billing.user_id).first()
            
            billings_report.append({
                "id": billing.id,
                "user_id": billing.user_id,
                "user_name": f"{user.fname} {user.lname}" if user else "Unknown",
                "user_email": user.email if user else "Unknown",
                "account_number": billing.card_number,
                "payment_method": billing.billing_type,
                "created_at": billing.created_at.isoformat() if billing.created_at else None,
            })

        # --- CATEGORIES REPORT ---
        main_categories_data = db.query(MainCategory).all()
        main_categories_report = []
        for category in main_categories_data:
            sub_categories_count = db.query(func.count(SubCategory.id)).filter(
                SubCategory.main_category_id == category.id
            ).scalar() or 0
            
            main_categories_report.append({
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "sub_categories_count": sub_categories_count,
                "created_at": category.created_at.isoformat() if category.created_at else None
            })

        sub_categories_data = db.query(SubCategory).all()
        sub_categories_report = []
        for category in sub_categories_data:
            product_categories_count = db.query(func.count(ProductCategory.id)).filter(
                ProductCategory.sub_category_id == category.id
            ).scalar() or 0
            
            sub_categories_report.append({
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "main_category_id": category.main_category_id,
                "product_categories_count": product_categories_count,
                "created_at": category.created_at.isoformat() if category.created_at else None
            })

        product_categories_data = db.query(ProductCategory).all()
        product_categories_report = []
        for category in product_categories_data:
            products_count = db.query(func.count(Product.id)).filter(
                Product.category_id == category.id
            ).scalar() or 0
            
            product_categories_report.append({
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "sub_category_id": category.sub_category_id,
                "products_count": products_count,
                "created_at": category.created_at.isoformat() if category.created_at else None
            })

        # --- LOGIN LOGS REPORT ---
        login_logs_data = db.query(LoginLogs).order_by(desc(LoginLogs.login_time)).limit(100).all()
        login_logs_report = []
        for log in login_logs_data:
            user = db.query(Users).filter(Users.id == log.user_id).first()
            
            login_logs_report.append({
                "id": log.id,
                "user_id": log.user_id,
                "user_name": f"{user.fname} {user.lname}" if user else "Unknown",
                "user_email": user.email if user else "Unknown",
                "ip_address": log.ip_address,
                "device_info": log.device_info,
                "login_time": log.login_time.isoformat() if log.login_time else None,
                "device_active": log.device_active
            })

        summary_stats = {
            "total_users": len(users_report),
            "total_products": len(products_report),
            "total_carts": len(carts_report),
            "total_wishlists": len(wishlists_report),
            "total_billings": len(billings_report),
            "total_main_categories": len(main_categories_report),
            "total_sub_categories": len(sub_categories_report),
            "total_product_categories": len(product_categories_report),
            "total_login_records": len(login_logs_report),
            "report_generated_at": datetime.now().isoformat(),
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }

        return {
            "summary": summary_stats,
            "users": users_report,
            "products": products_report,
            "carts": carts_report,
            "wishlists": wishlists_report,
            "billings": billings_report,
            "categories": {
                "main_categories": main_categories_report,
                "sub_categories": sub_categories_report,
                "product_categories": product_categories_report
            },
            "login_logs": login_logs_report
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating comprehensive report: {str(e)}")


@router.get("/export-report")
async def export_comprehensive_report(
    db: db_dependency,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json"  # Could be extended to support CSV, PDF, etc.
):
    """
    Export comprehensive report in different formats (without orders)
    """
    try:
        report_data = await get_comprehensive_report(db, start_date, end_date, include_details=True)
        
        if format == "json":
            return report_data
        elif format == "csv":
            # Placeholder for CSV export
            return {
                "message": "CSV export feature coming soon",
                "data": report_data
            }
        else:
            return report_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting report: {str(e)}")


@router.get("/analytics")
async def get_analytics_report(
    db: db_dependency,
    period: str = "30d"  # 7d, 30d, 90d, 1y
):
    """
    Get analytics data for charts and trends (without orders)
    """
    try:
        end_date = datetime.now()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        # User registration trends
        user_registrations = db.query(
            func.date(Users.created_at).label('date'),
            func.count(Users.id).label('count')
        ).filter(
            Users.created_at >= start_date
        ).group_by(
            func.date(Users.created_at)
        ).order_by('date').all()

        # Billing trends
        billing_trends = db.query(
            func.date(Billing.created_at).label('date'),
            func.count(Billing.id).label('count'),
        ).filter(
            Billing.created_at >= start_date
        ).group_by(
            func.date(Billing.created_at)
        ).order_by('date').all()

        # Top products by cart appearances
        top_products = db.query(
            CartItem.product_id,
            CartItem.quantity,
            func.sum(CartItem.quantity).label('total_quantity'),
            func.count(CartItem.cart_id).label('cart_appearances')
        ).group_by(
            CartItem.product_id, CartItem.quantity
        ).order_by(
            desc('total_quantity')
        ).limit(10).all()

        return {
            "period": period,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "user_registration_trends": [
                {"date": reg.date.isoformat() if reg.date else None, "count": reg.count}
                for reg in user_registrations
            ],
            "billing_trends": [
                {
                    "date": trend.date.isoformat() if trend.date else None,
                    "billing_count": trend.count,
                    "daily_revenue": float(trend.revenue) if trend.revenue else 0
                }
                for trend in billing_trends
            ],
            "top_products": [
                {
                    "product_id": product.product_id,
                    "product_name": product.product_name,
                    "total_quantity": product.total_quantity,
                    "cart_appearances": product.cart_appearances
                }
                for product in top_products
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating analytics: {str(e)}")
