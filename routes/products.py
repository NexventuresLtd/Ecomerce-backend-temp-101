# routes/product.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import base64
import re
import uuid
import logging

from db.VerifyToken import user_dependency  
from db.connection import db_dependency
from models.Products import Product
from models.Categories import ProductCategory
from schemas.productManagement.Products import (
    ProductCreate, ProductResponse, ProductUpdate, ProductImageSchema
)

router = APIRouter(prefix="/products", tags=["products"])

# ---------------- CONFIG ----------------
PRODUCT_IMAGE_FOLDER = "./static/images/products"
PRODUCT_BASE_URL = "static/images/products/"
os.makedirs(PRODUCT_IMAGE_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ---------------- HELPERS ----------------
def decode_base64(data: str):
    """Decode base64 image data with better error handling"""
    try:
        if not data:
            return None
        if "," in data:
            data = data.split(",", 1)[1]
        data = re.sub(r"[^A-Za-z0-9+/=]", "", data)
        missing_padding = len(data) % 4
        if missing_padding:
            data += "=" * (4 - missing_padding)
        return base64.b64decode(data)
    except Exception as e:
        logger.error(f"Base64 decoding error: {str(e)}")
        return None

def get_image_extension(data: bytes) -> str:
    """Detect image extension from bytes"""
    if data.startswith(b"\xFF\xD8"):
        return "jpg"
    elif data.startswith(b"\x89PNG"):
        return "png"
    elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    elif data.startswith(b"BM"):
        return "bmp"
    elif data.startswith(b"WEBP"):
        return "webp"
    else:
        # Default to jpg if unknown
        return "jpg"

def save_product_image(product_id: int, image_data: bytes, image_type: str = "main", image_index: int = 0) -> str:
    """Save product image to file system"""
    try:
        ext = get_image_extension(image_data)
        unique_id = uuid.uuid4().hex[:8]
        filename = f"product_{product_id}_{image_type}_{unique_id}.{ext}"
        filepath = os.path.join(PRODUCT_IMAGE_FOLDER, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        logger.info(f"Image saved: {filename}")
        return f"{PRODUCT_BASE_URL}{filename}"
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        raise

def process_single_image(product_id: int, image_url: str, image_type: str = "hover") -> Optional[str]:
    """Process a single image (for hover_image, tutorial_video, etc.)"""
    if not image_url:
        return None
        
    # Check if it's a base64 data URL
    if image_url.startswith('data:image'):
        image_bytes = decode_base64(image_url)
        if not image_bytes:
            logger.warning(f"{image_type} image failed base64 decoding")
            return None
            
        try:
            saved_url = save_product_image(product_id, image_bytes, image_type)
            logger.info(f"Successfully processed {image_type} image")
            return saved_url
        except Exception as e:
            logger.error(f"Error processing {image_type} image: {str(e)}")
            return None
    else:
        # If it's already a regular URL, use it as is
        logger.info(f"Using existing URL for {image_type} image")
        return image_url

def process_product_images_from_urls(product_id: int, images_data: List[ProductImageSchema]) -> List[Dict[str, Any]]:
    """Process images from base64 URLs in the existing schema"""
    processed_images = []
    
    for i, img_data in enumerate(images_data):
        logger.debug(f"Processing image {i}: {img_data.url[:100] if img_data.url else 'No URL'}")
        
        if not img_data.url:
            logger.warning(f"Image {i} has no URL")
            continue
            
        # Check if it's a base64 data URL
        if img_data.url.startswith('data:image'):
            image_bytes = decode_base64(img_data.url)
            if not image_bytes:
                logger.warning(f"Image {i} failed base64 decoding")
                continue
                
            try:
                image_url = save_product_image(product_id, image_bytes, "main", i)
                processed_images.append({
                    "url": image_url,
                    "is_primary": img_data.is_primary or False,
                    "alt_text": getattr(img_data, 'alt_text', f"Product image {i+1}")
                })
                logger.info(f"Successfully processed base64 image {i}")
            except Exception as e:
                logger.error(f"Error processing base64 image {i}: {str(e)}")
                continue
        else:
            # If it's already a regular URL, use it as is
            processed_images.append({
                "url": img_data.url,
                "is_primary": img_data.is_primary or False,
                "alt_text": getattr(img_data, 'alt_text', f"Product image {i+1}")
            })
            logger.info(f"Using existing URL for image {i}")
    
    return processed_images

def delete_old_image_files(product: Product):
    """Delete old image files (both main images and hover image)"""
    # Delete main product images
    if product.images:
        for image_data in product.images:
            if 'url' in image_data and image_data['url'].startswith(PRODUCT_BASE_URL):
                filename = image_data['url'].replace(PRODUCT_BASE_URL, '')
                filepath = os.path.join(PRODUCT_IMAGE_FOLDER, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"Deleted old image: {filename}")
    
    # Delete hover image
    if product.hover_image and product.hover_image.startswith(PRODUCT_BASE_URL):
        filename = product.hover_image.replace(PRODUCT_BASE_URL, '')
        filepath = os.path.join(PRODUCT_IMAGE_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted old hover image: {filename}")

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
    user: user_dependency
):
    """Create a new product with images"""
    try:
        logger.info("Starting product creation")
        
        if isinstance(user, HTTPException):
            raise user
        if not user["user_id"]:
            raise HTTPException(status=401, detail="Not Allowed To Perform This Action")
        
        product_data.owner_id = user["user_id"]
        
        # Check if category exists if provided
        if product_data.category_id:
            category = db.query(ProductCategory).filter(ProductCategory.id == product_data.category_id).first()
            if not category:
                raise HTTPException(status_code=400, detail="Category does not exist")
        
        # Validate that at least one image is provided
        if not product_data.images:
            raise HTTPException(status_code=400, detail="At least one image is required")
        
        logger.info(f"Received {len(product_data.images)} images")
        
        # Ensure only one primary image
        primary_count = sum(1 for img in product_data.images if img.is_primary)
        if primary_count > 1:
            raise HTTPException(status_code=400, detail="Only one image can be set as primary")
        
        # Create product first without images to get ID
        product_dict = product_data.model_dump()
        images_data = product_dict.pop('images')  # Remove images for now
        hover_image = product_dict.pop('hover_image', None)  # Remove hover_image for separate processing
        
        logger.info("Creating product in database")
        db_product = Product(**product_dict)
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product created with ID: {db_product.id}")
        
        try:
            # Process and save main images
            logger.info("Processing main images...")
            processed_images = process_product_images_from_urls(db_product.id, product_data.images)
            
            if not processed_images:
                logger.error("No valid images could be processed")
                raise HTTPException(status_code=400, detail="No valid images could be processed")
            
            logger.info(f"Successfully processed {len(processed_images)} main images")
            
            # If no primary image was specified, set the first one as primary
            if primary_count == 0:
                processed_images[0]["is_primary"] = True
                logger.info("Set first image as primary")
            
            # Process hover image if provided
            processed_hover_image = None
            if hover_image:
                logger.info("Processing hover image...")
                processed_hover_image = process_single_image(db_product.id, hover_image, "hover")
                if processed_hover_image:
                    logger.info("Hover image processed successfully")
                else:
                    logger.warning("Hover image processing failed")
            
            # Update product with image URLs
            db_product.images = processed_images
            db_product.hover_image = processed_hover_image
            db.commit()
            db.refresh(db_product)
            logger.info("Product updated with images successfully")
            
        except Exception as e:
            logger.error(f"Image processing failed: {str(e)}")
            # Clean up if image processing fails
            db.delete(db_product)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to process images: {str(e)}")
        
        return db_product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    db: db_dependency,
    product_id: int, 
    product_data: ProductUpdate, 
    user: user_dependency
):
    if isinstance(user, HTTPException):
        raise user
    
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if category exists if provided
    if product_data.category_id is not None:
        category = db.query(ProductCategory).filter(ProductCategory.id == product_data.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category does not exist")
    
    # Handle images if provided in update
    images_updated = False
    if product_data.images is not None:
        # Validate that at least one image is provided
        if not product_data.images:
            raise HTTPException(status_code=400, detail="At least one image is required")
        
        # Ensure only one primary image
        primary_count = sum(1 for img in product_data.images if img.is_primary)
        if primary_count > 1:
            raise HTTPException(status_code=400, detail="Only one image can be set as primary")
        
        images_updated = True
    
    # Handle hover image if provided in update
    hover_image_updated = product_data.hover_image is not None
    
    # Delete old image files if we're updating images
    if images_updated or hover_image_updated:
        delete_old_image_files(db_product)
    
    # Process main images if provided
    if images_updated:
        processed_images = process_product_images_from_urls(product_id, product_data.images)
        
        if not processed_images:
            raise HTTPException(status_code=400, detail="No valid images provided")
        
        # If no primary image was specified, set the first one as primary
        if primary_count == 0:
            processed_images[0]["is_primary"] = True
        
        # Update product with new images
        db_product.images = processed_images
    
    # Process hover image if provided
    if hover_image_updated:
        processed_hover_image = process_single_image(product_id, product_data.hover_image, "hover")
        db_product.hover_image = processed_hover_image
    
    # Update other fields
    update_data = product_data.model_dump(exclude_unset=True, exclude={'images', 'hover_image'})
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
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
    
    # Delete all associated image files
    delete_old_image_files(product)
    
    # Delete product from database
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}

@router.patch("/{product_id}/images/set-primary")
def set_primary_image(
    product_id: int,
    image_index: int,
    db: db_dependency,
    user: user_dependency
):
    """
    Set a specific image as primary by its index in the images array
    """
    if isinstance(user, HTTPException):
        raise user
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.images:
        raise HTTPException(status_code=400, detail="Product has no images")
    
    if image_index < 0 or image_index >= len(product.images):
        raise HTTPException(status_code=400, detail="Invalid image index")
    
    # Update all images to set is_primary=False
    for i, image in enumerate(product.images):
        image["is_primary"] = (i == image_index)
    
    db.commit()
    db.refresh(product)
    
    return {"message": "Primary image set successfully", "product": product}