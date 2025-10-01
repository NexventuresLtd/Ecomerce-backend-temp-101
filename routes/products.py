# routes/product.py
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import base64
import re
import uuid
import logging
import json
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Try to import image processing libraries
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not available. Image compression disabled.")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Advanced image compression disabled.")

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
PRODUCT_BASE_URL = "/static/images/products/"
os.makedirs(PRODUCT_IMAGE_FOLDER, exist_ok=True)

# Image optimization settings
IMAGE_QUALITY = 85  # JPEG quality (0-100)
MAX_WIDTH = 1200    # Maximum width for images
MAX_HEIGHT = 1200   # Maximum height for images
THUMBNAIL_SIZE = (400, 400)  # Thumbnail dimensions

# ---------------- HELPERS ----------------
def get_image_extension_from_content_type(content_type: str) -> str:
    """Get image extension from content type"""
    if content_type == "image/jpeg":
        return "jpg"
    elif content_type == "image/png":
        return "png"
    elif content_type == "image/gif":
        return "gif"
    elif content_type == "image/webp":
        return "webp"
    elif content_type == "image/bmp":
        return "bmp"
    else:
        return "jpg"  # Default to jpg

def compress_image_pil(image_data: bytes, max_size=(MAX_WIDTH, MAX_HEIGHT), quality=IMAGE_QUALITY) -> bytes:
    """Compress image using PIL/Pillow"""
    try:
        with Image.open(BytesIO(image_data)) as img:
            # Convert to RGB if necessary (for JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize if too large
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save with compression
            output = BytesIO()
            img.save(output, format='JPEG', optimize=True, quality=quality, progressive=True)
            return output.getvalue()
    except Exception as e:
        logger.error(f"PIL compression failed: {str(e)}")
        return image_data  # Return original if compression fails

def compress_image_opencv(image_data: bytes, max_size=(MAX_WIDTH, MAX_HEIGHT), quality=IMAGE_QUALITY) -> bytes:
    """Compress image using OpenCV (better for photos)"""
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return image_data
        
        # Get current dimensions
        height, width = img.shape[:2]
        
        # Calculate resize dimensions
        if width > max_size[0] or height > max_size[1]:
            ratio = min(max_size[0] / width, max_size[1] / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Encode with compression
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, encoded_img = cv2.imencode('.jpg', img, encode_param)
        
        if success:
            return encoded_img.tobytes()
        else:
            return image_data
    except Exception as e:
        logger.error(f"OpenCV compression failed: {str(e)}")
        return image_data

def create_thumbnail(image_data: bytes, size=THUMBNAIL_SIZE) -> bytes:
    """Create a thumbnail version of the image"""
    try:
        with Image.open(BytesIO(image_data)) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            output = BytesIO()
            img.save(output, format='JPEG', optimize=True, quality=80)
            return output.getvalue()
    except Exception as e:
        logger.error(f"Thumbnail creation failed: {str(e)}")
        return image_data

def optimize_image(image_data: bytes, image_type: str = "main") -> bytes:
    """Optimize image based on available libraries and image type"""
    original_size = len(image_data)
    
    # Choose compression method based on available libraries
    if CV2_AVAILABLE and image_type == "main":
        compressed_data = compress_image_opencv(image_data)
    elif PIL_AVAILABLE:
        compressed_data = compress_image_pil(image_data)
    else:
        compressed_data = image_data  # No compression available
    
    compressed_size = len(compressed_data)
    compression_ratio = (original_size - compressed_size) / original_size * 100
    
    logger.info(f"Image compressed: {original_size/1024:.1f}KB -> {compressed_size/1024:.1f}KB ({compression_ratio:.1f}% reduction)")
    
    return compressed_data

def save_product_image_from_file(product_id: int, file: UploadFile, image_type: str = "main") -> Dict[str, str]:
    """Save product image from uploaded file with multiple versions"""
    try:
        # Read file content
        file_content = file.file.read()
        
        # Get file extension
        ext = get_image_extension_from_content_type(file.content_type)
        unique_id = uuid.uuid4().hex[:8]
        
        # Optimize main image
        optimized_data = optimize_image(file_content, image_type)
        
        # Save main image
        main_filename = f"product_{product_id}_{image_type}_{unique_id}.{ext}"
        main_filepath = os.path.join(PRODUCT_IMAGE_FOLDER, main_filename)
        
        with open(main_filepath, "wb") as f:
            f.write(optimized_data)
        
        # Create and save thumbnail for main images
        thumbnail_url = None
        if image_type == "main" and PIL_AVAILABLE:
            thumbnail_data = create_thumbnail(file_content)
            thumb_filename = f"product_{product_id}_{image_type}_{unique_id}_thumb.{ext}"
            thumb_filepath = os.path.join(PRODUCT_IMAGE_FOLDER, thumb_filename)
            
            with open(thumb_filepath, "wb") as f:
                f.write(thumbnail_data)
            
            thumbnail_url = f"{PRODUCT_BASE_URL}{thumb_filename}"
        
        logger.info(f"Image saved: {main_filename} (thumbnail: {thumbnail_url})")
        
        return {
            "main": f"{PRODUCT_BASE_URL}{main_filename}",
            "thumbnail": thumbnail_url
        }
        
    except Exception as e:
        logger.error(f"Error saving image from file: {str(e)}")
        raise

def delete_single_image_file(image_url: str):
    """Delete a single image file and its thumbnail if they exist"""
    if image_url and image_url.startswith(PRODUCT_BASE_URL):
        filename = image_url.replace(PRODUCT_BASE_URL, '')
        filepath = os.path.join(PRODUCT_IMAGE_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted image file: {filename}")
        
        # Also try to delete thumbnail if it exists
        thumb_filename = filename.replace('.', '_thumb.')
        thumb_filepath = os.path.join(PRODUCT_IMAGE_FOLDER, thumb_filename)
        if os.path.exists(thumb_filepath):
            os.remove(thumb_filepath)
            logger.info(f"Deleted thumbnail file: {thumb_filename}")

def delete_old_hover_image_files(product: Product):
    """Delete only hover image files"""
    # Delete hover image
    if product.hover_image and product.hover_image.startswith(PRODUCT_BASE_URL):
        filename = product.hover_image.replace(PRODUCT_BASE_URL, '')
        filepath = os.path.join(PRODUCT_IMAGE_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted old hover image: {filename}")

def delete_old_main_image_files(product: Product):
    """Delete only main product image files (not hover image)"""
    # Delete main product images and thumbnails
    if product.images:
        for image_data in product.images:
            # Delete main image
            if 'url' in image_data and image_data['url'].startswith(PRODUCT_BASE_URL):
                filename = image_data['url'].replace(PRODUCT_BASE_URL, '')
                filepath = os.path.join(PRODUCT_IMAGE_FOLDER, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"Deleted old image: {filename}")
            
            # Delete thumbnail if exists
            if 'thumbnail' in image_data and image_data['thumbnail'] and image_data['thumbnail'].startswith(PRODUCT_BASE_URL):
                thumb_filename = image_data['thumbnail'].replace(PRODUCT_BASE_URL, '')
                thumb_filepath = os.path.join(PRODUCT_IMAGE_FOLDER, thumb_filename)
                if os.path.exists(thumb_filepath):
                    os.remove(thumb_filepath)
                    logger.info(f"Deleted old thumbnail: {thumb_filename}")

# Custom form field parser for optional integers
def parse_optional_int(value: Optional[str]) -> Optional[int]:
    """Parse optional integer from form data, handling empty strings"""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def parse_optional_float(value: Optional[str]) -> Optional[float]:
    """Parse optional float from form data, handling empty strings"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def parse_optional_bool(value: Optional[str]) -> Optional[bool]:
    """Parse optional boolean from form data"""
    if value is None or value == "":
        return None
    return value.lower() in ['true', '1', 'yes', 'on']

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
async def create_product(
    db: db_dependency,
    user: user_dependency,
    # Form fields
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    instock: int = Form(...),
    original_price: Optional[float] = Form(None),
    discount: Optional[float] = Form(None),
    is_new: bool = Form(False),
    is_featured: bool = Form(False),
    is_active: bool = Form(True),
    delivery_fee: Optional[str] = Form(None),
    brock: Optional[str] = Form(None),
    returnDay: Optional[str] = Form(None),
    warranty: Optional[str] = Form(None),
    tutorial_video: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    features: Optional[str] = Form(None),
    colors: Optional[str] = Form(None),
    # File fields
    images: List[UploadFile] = File(...),
    hover_image: Optional[UploadFile] = File(None)
):
    """Create a new product with file uploads"""
    try:
        logger.info("Starting product creation")
        
        if isinstance(user, HTTPException):
            raise user
        if not user["user_id"]:
            raise HTTPException(status=401, detail="Not Allowed To Perform This Action")
        
        # Check if category exists
        category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category does not exist")
        
        # Validate that at least one image is provided
        if not images:
            raise HTTPException(status_code=400, detail="At least one image is required")
        
        logger.info(f"Received {len(images)} images")
        
        # Parse JSON fields
        tags_list = json.loads(tags) if tags else []
        features_list = json.loads(features) if features else []
        colors_list = json.loads(colors) if colors else []
        
        # Create product first without images to get ID
        product_data = {
            "title": title,
            "description": description,
            "price": price,
            "category_id": category_id,
            "instock": instock,
            "original_price": original_price,
            "discount": discount,
            "is_new": is_new,
            "is_featured": is_featured,
            "is_active": is_active,
            "delivery_fee": delivery_fee,
            "brock": brock,
            "returnDay": returnDay,
            "warranty": warranty,
            "tutorial_video": tutorial_video,
            "tags": tags_list,
            "features": features_list,
            "colors": colors_list,
            "owner_id": user["user_id"]
        }
        
        logger.info("Creating product in database")
        db_product = Product(**product_data)
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product created with ID: {db_product.id}")
        
        try:
            # Process and save main images
            logger.info("Processing main images...")
            processed_images = []
            
            for i, image_file in enumerate(images):
                try:
                    saved_urls = save_product_image_from_file(db_product.id, image_file, "main")
                    image_info = {
                        "url": saved_urls["main"],
                        "is_primary": i == 0,  # First image is primary by default
                        "alt_text": f"Product image {i+1}"
                    }
                    
                    # Add thumbnail URL if available
                    if saved_urls["thumbnail"]:
                        image_info["thumbnail"] = saved_urls["thumbnail"]
                        
                    processed_images.append(image_info)
                    logger.info(f"Successfully processed image {i}")
                    
                except Exception as e:
                    logger.error(f"Error processing image {i}: {str(e)}")
                    continue
            
            if not processed_images:
                logger.error("No valid images could be processed")
                raise HTTPException(status_code=400, detail="No valid images could be processed")
            
            logger.info(f"Successfully processed {len(processed_images)} main images")
            
            # Process hover image if provided
            processed_hover_image = None
            if hover_image:
                logger.info("Processing hover image...")
                try:
                    saved_urls = save_product_image_from_file(db_product.id, hover_image, "hover")
                    processed_hover_image = saved_urls["main"]
                    logger.info("Hover image processed successfully")
                except Exception as e:
                    logger.error(f"Error processing hover image: {str(e)}")
                    # Continue without hover image if processing fails
            
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
async def update_product(
    db: db_dependency,
    product_id: int,
    user: user_dependency,
    # Form fields (all optional for updates) - use string then parse
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[str] = Form(None),  # Changed to string for parsing
    category_id: Optional[str] = Form(None),  # Changed to string for parsing
    instock: Optional[str] = Form(None),  # Changed to string for parsing
    original_price: Optional[str] = Form(None),  # Changed to string for parsing
    discount: Optional[str] = Form(None),  # Changed to string for parsing
    is_new: Optional[str] = Form(None),  # Changed to string for parsing
    is_featured: Optional[str] = Form(None),  # Changed to string for parsing
    is_active: Optional[str] = Form(None),  # Changed to string for parsing
    delivery_fee: Optional[str] = Form(None),
    brock: Optional[str] = Form(None),
    returnDay: Optional[str] = Form(None),
    warranty: Optional[str] = Form(None),
    tutorial_video: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    features: Optional[str] = Form(None),
    colors: Optional[str] = Form(None),
    # File fields
    images: Optional[List[UploadFile]] = File(None),
    hover_image: Optional[UploadFile] = File(None),
    keep_existing_images: bool = Form(True)
):
    """Update product with file uploads"""
    if isinstance(user, HTTPException):
        raise user
    
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Parse form data with proper type handling
    parsed_category_id = parse_optional_int(category_id)
    
    # Check if category exists if provided and not empty
    if parsed_category_id is not None:
        category = db.query(ProductCategory).filter(ProductCategory.id == parsed_category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category does not exist")
    
    # Store current state for comparison
    current_images = db_product.images.copy() if db_product.images else []
    current_hover_image = db_product.hover_image
    
    try:
        # Process main images if provided
        if images is not None:
            logger.info(f"Processing {len(images)} new images for update")
            
            # Delete old images if not keeping them
            if not keep_existing_images:
                delete_old_main_image_files(db_product)
                processed_images = []
            else:
                processed_images = current_images.copy()
            
            # Process new images
            for i, image_file in enumerate(images):
                try:
                    saved_urls = save_product_image_from_file(product_id, image_file, "main")
                    image_info = {
                        "url": saved_urls["main"],
                        "is_primary": len(processed_images) == 0,  # First new image is primary if no existing images
                        "alt_text": f"Product image {len(processed_images) + 1}"
                    }
                    
                    # Add thumbnail URL if available
                    if saved_urls["thumbnail"]:
                        image_info["thumbnail"] = saved_urls["thumbnail"]
                        
                    processed_images.append(image_info)
                    logger.info(f"Successfully processed new image {i}")
                    
                except Exception as e:
                    logger.error(f"Error processing new image {i}: {str(e)}")
                    continue
            
            if not processed_images and images:
                raise HTTPException(status_code=400, detail="No valid images could be processed")
            
            db_product.images = processed_images
            logger.info(f"Updated main images: {len(processed_images)} images total")
        
        # Process hover image if provided
        if hover_image is not None:
            # Delete old hover image
            delete_old_hover_image_files(db_product)
            
            try:
                saved_urls = save_product_image_from_file(product_id, hover_image, "hover")
                db_product.hover_image = saved_urls["main"]
                logger.info("Hover image updated successfully")
            except Exception as e:
                logger.error(f"Error processing hover image: {str(e)}")
                # Set to None if processing fails
                db_product.hover_image = None
        
        # Update other fields with parsed values
        update_data = {}
        
        # Simple string fields
        string_fields = {
            "title": title,
            "description": description,
            "delivery_fee": delivery_fee,
            "brock": brock,
            "returnDay": returnDay,
            "warranty": warranty,
            "tutorial_video": tutorial_video
        }
        
        for field, value in string_fields.items():
            if value is not None:
                update_data[field] = value
        
        # Numeric fields with parsing
        if price is not None:
            update_data["price"] = parse_optional_float(price)
        if instock is not None:
            update_data["instock"] = parse_optional_int(instock)
        if original_price is not None:
            update_data["original_price"] = parse_optional_float(original_price)
        if discount is not None:
            update_data["discount"] = parse_optional_float(discount)
        if parsed_category_id is not None:
            update_data["category_id"] = parsed_category_id
        
        # Boolean fields with parsing
        if is_new is not None:
            update_data["is_new"] = parse_optional_bool(is_new)
        if is_featured is not None:
            update_data["is_featured"] = parse_optional_bool(is_featured)
        if is_active is not None:
            update_data["is_active"] = parse_optional_bool(is_active)
        
        # Parse and update JSON fields if provided
        if tags is not None:
            db_product.tags = json.loads(tags) if tags else []
        if features is not None:
            db_product.features = json.loads(features) if features else []
        if colors is not None:
            db_product.colors = json.loads(colors) if colors else []
        
        # Update simple fields
        for key, value in update_data.items():
            if value is not None:
                setattr(db_product, key, value)
        
        db.commit()
        db.refresh(db_product)
        
        logger.info(f"Product {product_id} updated successfully")
        
        return db_product
        
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")

@router.post("/{product_id}/images")
async def add_product_images(
    product_id: int,
    db: db_dependency,
    user: user_dependency,
    images: List[UploadFile] = File(...)
):
    """Add images to an existing product"""
    if isinstance(user, HTTPException):
        raise user
    
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")
    
    try:
        current_images = db_product.images.copy() if db_product.images else []
        new_images = []
        
        for image_file in images:
            try:
                saved_urls = save_product_image_from_file(product_id, image_file, "main")
                image_info = {
                    "url": saved_urls["main"],
                    "is_primary": False,  # New images are not primary by default
                    "alt_text": f"Product image {len(current_images) + len(new_images) + 1}"
                }
                
                # Add thumbnail URL if available
                if saved_urls["thumbnail"]:
                    image_info["thumbnail"] = saved_urls["thumbnail"]
                    
                new_images.append(image_info)
                logger.info(f"Successfully added new image")
                
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                continue
        
        if not new_images:
            raise HTTPException(status_code=400, detail="No valid images could be processed")
        
        # Combine existing and new images
        db_product.images = current_images + new_images
        db.commit()
        db.refresh(db_product)
        
        return {
            "message": f"Successfully added {len(new_images)} images",
            "product": db_product
        }
        
    except Exception as e:
        logger.error(f"Error adding images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add images: {str(e)}")

@router.delete("/{product_id}/images/{image_index}")
async def delete_product_image(
    product_id: int,
    image_index: int,
    db: db_dependency,
    user: user_dependency
):
    """Delete a specific image from a product by its index"""
    if isinstance(user, HTTPException):
        raise user
    
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not db_product.images:
        raise HTTPException(status_code=400, detail="Product has no images")
    
    if image_index < 0 or image_index >= len(db_product.images):
        raise HTTPException(status_code=400, detail="Invalid image index")
    
    try:
        # Get the image to delete
        image_to_delete = db_product.images[image_index]
        
        # Delete the image files
        if 'url' in image_to_delete and image_to_delete['url'].startswith(PRODUCT_BASE_URL):
            delete_single_image_file(image_to_delete['url'])
        
        # Remove from images array
        updated_images = [img for i, img in enumerate(db_product.images) if i != image_index]
        
        # If we deleted the primary image and there are other images, set the first one as primary
        if image_to_delete.get('is_primary') and updated_images:
            updated_images[0]['is_primary'] = True
        
        db_product.images = updated_images
        db.commit()
        
        return {"message": "Image deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")

@router.delete("/{product_id}")
def delete_product(product_id: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete all associated image files
    delete_old_main_image_files(product)
    delete_old_hover_image_files(product)
    
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