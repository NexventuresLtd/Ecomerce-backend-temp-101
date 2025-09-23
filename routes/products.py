# routes/product.py
import os

from fastapi import (
    APIRouter,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Depends
)
from sqlalchemy.orm import joinedload
from typing import List, Optional
from datetime import datetime
from db.VerifyToken import user_dependency
from db.connection import db_dependency
from models.Products import Product
from models.Categories import ProductCategory
from schemas.productManagement.Products import (
    ProductResponse,
)
from functions.ImageSaver import save_uploaded_file
router = APIRouter(prefix="/products", tags=["products"])


# ---------------- ENDPOINTS ----------------
@router.get("/", response_model=List[ProductResponse])
def get_products(db: db_dependency, skip: int = 0, limit: int = 100):
    return (
        db.query(Product)
        .options(joinedload(Product.category))
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: db_dependency):
    product = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    db: db_dependency,
    user: user_dependency,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: Optional[int] = Form(None),
    images: List[UploadFile] = File(...),
):
    if isinstance(user, HTTPException):
        raise user
    if not user["user_id"]:
        raise HTTPException(status=401, detail="Not Allowed To Perform This Action")

    # Validate category
    if category_id:
        category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category does not exist")

    # Validate images
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")

    # Create product first
    db_product = Product(
        name=name,
        description=description,
        price=price,
        category_id=category_id,
        owner_id=user["user_id"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Save images
    image_paths = []
    for idx, file in enumerate(images):
        path = save_uploaded_file(file, db_product.id, idx)
        image_paths.append({"url": path, "is_primary": idx == 0})

    # Attach images to product (assuming Product.images is JSON or relationship)
    db_product.images = image_paths
    db.commit()
    db.refresh(db_product)

    return db_product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    db: db_dependency,
    user: user_dependency,
    product_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    category_id: Optional[int] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
):
    if isinstance(user, HTTPException):
        raise user

    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate category
    if category_id is not None:
        category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category does not exist")

    # Update fields
    if name is not None:
        db_product.name = name
    if description is not None:
        db_product.description = description
    if price is not None:
        db_product.price = price
    if category_id is not None:
        db_product.category_id = category_id

    # Handle new images
    if images is not None and len(images) > 0:
        image_paths = []
        for idx, file in enumerate(images):
            path = save_uploaded_file(file, db_product.id, idx)
            image_paths.append({"url": path, "is_primary": idx == 0})
        db_product.images = image_paths

    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


@router.patch("/{product_id}/images/set-primary")
def set_primary_image(
    product_id: int,
    image_index: int,
    db: db_dependency,
    user: user_dependency,
):
    if isinstance(user, HTTPException):
        raise user

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if image_index < 0 or image_index >= len(product.images):
        raise HTTPException(status_code=400, detail="Invalid image index")

    # Update all images to set is_primary=False
    for i, image in enumerate(product.images):
        image["is_primary"] = (i == image_index)

    db.commit()
    db.refresh(product)

    return {"message": "Primary image set successfully", "product": product}
