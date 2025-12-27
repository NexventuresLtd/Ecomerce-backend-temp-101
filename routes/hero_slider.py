# routes/hero_slider.py
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends, Query
from typing import Optional, List, Dict
import os
import uuid
import logging
from io import BytesIO

# Try to import image processing libraries
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not available. Image compression disabled.")

from db.connection import db_dependency
from models.hero_slider import HeroSlider
from schemas.hero_slider import HeroSliderCreate, HeroSliderUpdate, HeroSliderResponse

router = APIRouter(prefix="/hero-sliders", tags=["Hero Sliders"])

# Set up logging
logger = logging.getLogger(__name__)

# ---------------- CONFIG ----------------
HERO_IMAGE_FOLDER = "./static/images/hero-sliders"
HERO_BASE_URL = "/static/images/hero-sliders/"
os.makedirs(HERO_IMAGE_FOLDER, exist_ok=True)

# Image optimization settings
IMAGE_QUALITY = 85  # JPEG quality (0-100)
MAX_WIDTH = 1920    # Maximum width for hero images (wider for banners)
MAX_HEIGHT = 800    # Maximum height for hero images
THUMBNAIL_SIZE = (400, 200)  # Thumbnail dimensions for hero sliders

# ---------------- IMAGE HELPERS ----------------
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
            
            # Calculate aspect ratio preserving resize
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save with compression
            output = BytesIO()
            img.save(output, format='JPEG', optimize=True, quality=quality, progressive=True)
            return output.getvalue()
    except Exception as e:
        logger.error(f"PIL compression failed: {str(e)}")
        return image_data  # Return original if compression fails

def create_thumbnail(image_data: bytes, size=THUMBNAIL_SIZE) -> bytes:
    """Create a thumbnail version of the hero image"""
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

def optimize_image(image_data: bytes) -> bytes:
    """Optimize hero image"""
    original_size = len(image_data)
    
    if PIL_AVAILABLE:
        compressed_data = compress_image_pil(image_data)
    else:
        compressed_data = image_data  # No compression available
    
    compressed_size = len(compressed_data)
    compression_ratio = (original_size - compressed_size) / original_size * 100
    
    logger.info(f"Hero image compressed: {original_size/1024:.1f}KB -> {compressed_size/1024:.1f}KB ({compression_ratio:.1f}% reduction)")
    
    return compressed_data

def save_hero_image_from_file(slider_id: str, file: UploadFile) -> Dict[str, str]:
    """Save hero slider image from uploaded file with thumbnail"""
    try:
        # Read file content
        file_content = file.file.read()
        
        # Get file extension
        ext = get_image_extension_from_content_type(file.content_type)
        unique_id = uuid.uuid4().hex[:8]
        
        # Optimize main image
        optimized_data = optimize_image(file_content)
        
        # Save main image
        main_filename = f"hero_{slider_id}_{unique_id}.{ext}"
        main_filepath = os.path.join(HERO_IMAGE_FOLDER, main_filename)
        
        with open(main_filepath, "wb") as f:
            f.write(optimized_data)
        
        # Create and save thumbnail
        thumbnail_url = None
        if PIL_AVAILABLE:
            thumbnail_data = create_thumbnail(file_content)
            thumb_filename = f"hero_{slider_id}_{unique_id}_thumb.{ext}"
            thumb_filepath = os.path.join(HERO_IMAGE_FOLDER, thumb_filename)
            
            with open(thumb_filepath, "wb") as f:
                f.write(thumbnail_data)
            
            thumbnail_url = f"{HERO_BASE_URL}{thumb_filename}"
        
        logger.info(f"Hero image saved: {main_filename} (thumbnail: {thumbnail_url})")
        
        return {
            "main": f"{HERO_BASE_URL}{main_filename}",
            "thumbnail": thumbnail_url
        }
        
    except Exception as e:
        logger.error(f"Error saving hero image: {str(e)}")
        raise

def delete_hero_image_file(image_url: str):
    """Delete a hero image file and its thumbnail if they exist"""
    if image_url and image_url.startswith(HERO_BASE_URL):
        filename = image_url.replace(HERO_BASE_URL, '')
        filepath = os.path.join(HERO_IMAGE_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted hero image file: {filename}")
        
        # Also try to delete thumbnail if it exists
        thumb_filename = filename.replace('.', '_thumb.')
        thumb_filepath = os.path.join(HERO_IMAGE_FOLDER, thumb_filename)
        if os.path.exists(thumb_filepath):
            os.remove(thumb_filepath)
            logger.info(f"Deleted hero thumbnail file: {thumb_filename}")

# ---------------- CRUD ENDPOINTS ----------------
# ---------------- CREATE ----------------
@router.post("/", response_model=HeroSliderResponse, status_code=status.HTTP_201_CREATED)
async def create_hero_slider(
    db: db_dependency,
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    image: UploadFile = File(...),
):
    """Create a new hero slider with image upload"""
    try:
        logger.info("Starting hero slider creation")
        
        # Validate image file
        if not image:
            raise HTTPException(status_code=400, detail="Image is required")
        
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Uploaded file must be an image")
        
        # Generate UUID for slider FIRST
        slider_id = str(uuid.uuid4())
        
        # **FIXED: Save the image FIRST to get the URL**
        logger.info("Processing and saving hero image...")
        saved_urls = save_hero_image_from_file(slider_id, image)
        image_url = saved_urls["main"]
        
        # **FIXED: Create slider WITH the image URL**
        slider_data = {
            "title": title,
            "subtitle": subtitle,
            "image": image_url  # Add the image URL here
        }
        
        logger.info("Creating hero slider in database with image")
        new_slider = HeroSlider(**slider_data)
        db.add(new_slider)
        db.commit()
        db.refresh(new_slider)
        logger.info(f"Hero slider created with ID: {new_slider.id}")
        
        return new_slider
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_hero_slider: {str(e)}")
        # If we saved the image but failed to create the database record,
        # we should clean up the image file
        try:
            if 'saved_urls' in locals() and saved_urls.get("main"):
                delete_hero_image_file(saved_urls["main"])
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ---------------- READ ALL ----------------
@router.get("/", response_model=list[HeroSliderResponse])
def get_hero_sliders(db: db_dependency, skip: int = 0, limit: int = 20):
    """Get all hero sliders with pagination"""
    return db.query(HeroSlider).order_by(HeroSlider.created_at.desc()).offset(skip).limit(limit).all()

# ---------------- READ ONE ----------------
@router.get("/{slider_id}", response_model=HeroSliderResponse)
def get_hero_slider(slider_id: str, db: db_dependency):
    """Get a specific hero slider by ID"""
    slider = db.query(HeroSlider).filter(HeroSlider.id == slider_id).first()
    if not slider:
        raise HTTPException(status_code=404, detail="Hero slider not found")
    return slider

# ---------------- UPDATE ----------------
@router.put("/{slider_id}", response_model=HeroSliderResponse)
async def update_hero_slider(
    slider_id: str,
    db: db_dependency,
    title: Optional[str] = Form(None),
    subtitle: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    """Update a hero slider with optional image update"""
    try:
        slider = db.query(HeroSlider).filter(HeroSlider.id == slider_id).first()
        
        if not slider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hero slider not found")
        
        # Store current image URL for cleanup if needed
        current_image_url = slider.image
        
        # Update text fields if provided
        if title is not None:
            slider.title = title
        if subtitle is not None:
            slider.subtitle = subtitle
        
        # Process image if provided
        if image is not None:
            # Validate new image
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Uploaded file must be an image")
            
            # Save new image
            saved_urls = save_hero_image_from_file(slider_id, image)
            slider.image = saved_urls["main"]
            
            # Delete old image file
            if current_image_url:
                delete_hero_image_file(current_image_url)
        
        db.commit()
        db.refresh(slider)
        logger.info(f"Hero slider {slider_id} updated successfully")
        
        return slider
        
    except Exception as e:
        logger.error(f"Error updating hero slider: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update hero slider: {str(e)}")

# ---------------- UPDATE PARTIAL (PATCH) ----------------
@router.patch("/{slider_id}", response_model=HeroSliderResponse)
async def partial_update_hero_slider(
    slider_id: str,
    slider_data: HeroSliderUpdate,
    db: db_dependency
):
    """Partially update a hero slider (without image upload)"""
    slider = db.query(HeroSlider).filter(HeroSlider.id == slider_id).first()
    
    if not slider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hero slider not found")
    
    # Update only provided fields
    update_data = slider_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slider, field, value)
    
    db.commit()
    db.refresh(slider)
    
    return slider

# ---------------- DELETE ----------------
@router.delete("/{slider_id}")
def delete_hero_slider(slider_id: str, db: db_dependency):
    """Delete a hero slider and its associated image files"""
    slider = db.query(HeroSlider).filter(HeroSlider.id == slider_id).first()
    
    if not slider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hero slider not found")
    
    # Delete associated image files
    if slider.image:
        delete_hero_image_file(slider.image)
    
    # Delete from database
    db.delete(slider)
    db.commit()
    
    return {"message": "Hero slider deleted successfully"}

# ---------------- GET ACTIVE SLIDERS ----------------
@router.get("/active/all", response_model=list[HeroSliderResponse])
def get_active_hero_sliders(db: db_dependency):
    """Get all hero sliders (you can add filtering logic here if needed)"""
    return db.query(HeroSlider).order_by(HeroSlider.created_at.desc()).all()

# ---------------- UPDATE IMAGE ONLY ----------------
@router.put("/{slider_id}/image")
async def update_hero_slider_image(
    db: db_dependency,
    slider_id: str,
    image: UploadFile = File(...),
):
    """Update only the image of a hero slider"""
    try:
        slider = db.query(HeroSlider).filter(HeroSlider.id == slider_id).first()
        
        if not slider:
            raise HTTPException(status_code=404, detail="Hero slider not found")
        
        # Validate image
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Uploaded file must be an image")
        
        # Store current image URL for cleanup
        current_image_url = slider.image
        
        # Save new image
        saved_urls = save_hero_image_from_file(slider_id, image)
        slider.image = saved_urls["main"]
        
        # Delete old image file
        if current_image_url:
            delete_hero_image_file(current_image_url)
        
        db.commit()
        db.refresh(slider)
        
        return {
            "message": "Image updated successfully",
            "slider": slider
        }
        
    except Exception as e:
        logger.error(f"Error updating hero slider image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update image: {str(e)}")

# ---------------- GET SLIDERS WITH THUMBNAILS ----------------
@router.get("/with-thumbnails/all")
def get_hero_sliders_with_thumbnails(db: db_dependency):
    """Get all hero sliders with thumbnail URLs if available"""
    sliders = db.query(HeroSlider).order_by(HeroSlider.created_at.desc()).all()
    
    result = []
    for slider in sliders:
        slider_dict = {
            "id": slider.id,
            "title": slider.title,
            "subtitle": slider.subtitle,
            "image": slider.image,
            "created_at": slider.created_at,
            "updated_at": slider.updated_at
        }
        
        # Try to generate thumbnail URL from main image
        if slider.image and slider.image.startswith(HERO_BASE_URL):
            main_filename = slider.image.replace(HERO_BASE_URL, '')
            thumb_filename = main_filename.replace('.', '_thumb.')
            thumb_path = os.path.join(HERO_IMAGE_FOLDER, thumb_filename)
            
            if os.path.exists(thumb_path):
                slider_dict["thumbnail"] = f"{HERO_BASE_URL}{thumb_filename}"
        
        result.append(slider_dict)
    
    return result