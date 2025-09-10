# routes/product.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime

from db.connection import db_dependency
from models.Products import Product
from models.Categories import ProductCategory
from schemas.productManagement.Products import (
    ProductCreate, ProductResponse, ProductUpdate, ProductResponse, ProductImageSchema
)

router = APIRouter(prefix="/products", tags=["products"])

# Product endpoints
@router.get("/", response_model=List[ProductResponse])
def get_products(
    db: db_dependency,
    skip: int = 0, 
    limit: int = 100, 
):
    return db.query(Product).options(
        joinedload(Product.category)
    ).offset(skip).limit(limit).all()

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: db_dependency):
    product = db.query(Product).options(
        joinedload(Product.category)
    ).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    db: db_dependency,
    product_data: ProductCreate,
):
    # Check if category exists if provided
    if product_data.category_id:
        category = db.query(ProductCategory).filter(ProductCategory.id == product_data.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category does not exist")
    
    # Validate that at least one image is provided
    if not product_data.images:
        raise HTTPException(status_code=400, detail="At least one image is required")
    
    # Ensure only one primary image - FIXED: use .is_primary instead of .get()
    primary_count = sum(1 for img in product_data.images if img.is_primary)
    if primary_count > 1:
        raise HTTPException(status_code=400, detail="Only one image can be set as primary")
    
    # If no primary image is specified, set the first one as primary
    if primary_count == 0 and product_data.images:
        # Convert to dict to modify
        images_data = [img.model_dump() for img in product_data.images]
        images_data[0]["is_primary"] = True
        product_data.images = images_data
    
    db_product = Product(**product_data.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    db: db_dependency,
    product_id: int, 
    product_data: ProductUpdate, 
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if category exists if provided
    if product_data.category_id is not None:
        category = db.query(ProductCategory).filter(ProductCategory.id == product_data.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category does not exist")
    
    # Handle images if provided in update
    if product_data.images is not None:
        # Validate that at least one image is provided
        if not product_data.images:
            raise HTTPException(status_code=400, detail="At least one image is required")
        
        # Ensure only one primary image - FIXED: use .is_primary instead of .get()
        primary_count = sum(1 for img in product_data.images if img.is_primary)
        if primary_count > 1:
            raise HTTPException(status_code=400, detail="Only one image can be set as primary")
        
        # If no primary image is specified, set the first one as primary
        if primary_count == 0 and product_data.images:
            # Convert to dict to modify
            images_data = [img.model_dump() for img in product_data.images]
            images_data[0]["is_primary"] = True
            product_data.images = images_data
    
    # Update fields
    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{product_id}")
def delete_product(product_id: int, db: db_dependency):
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
    db: db_dependency
):
    """
    Set a specific image as primary by its index in the images array
    """
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