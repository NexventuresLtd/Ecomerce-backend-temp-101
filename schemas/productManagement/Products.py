# schemas/product.py
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, List, Dict, Any

class ProductImageSchema(BaseModel):
    url: str
    is_primary: bool = False  # Default value if not provided

class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    discount: Optional[float] = Field(None, ge=0, le=100)
    rating: float = Field(0.0, ge=0, le=5)
    is_new: str = "used"
    is_featured: bool = False
    is_active: bool = True
    reviews_count: int = Field(0, ge=0)
    instock: int = Field(0, ge=0)
    delivery_fee: Optional[str] = None
    brock: Optional[str] = None
    returnDay: Optional[str] = None
    warranty: Optional[str] = None
    hover_image: Optional[str] = None
    owner_id: Optional[int] = None
    tutorial_video: Optional[str] = None
    tags: List[str] = []
    features: List[str] = []
    colors: List[Dict[str, Any]] = []
    category_id: Optional[Any] = None
    images: List[ProductImageSchema] = Field(..., min_items=1, description="List of product images")

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    discount: Optional[float] = Field(None, ge=0, le=100)
    rating: Optional[float] = Field(None, ge=0, le=5)
    warranty: Optional[str] = None
    is_new: Optional[str] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    reviews_count: Optional[int] = Field(None, ge=0)
    instock: Optional[int] = Field(None, ge=0)
    delivery_fee: Optional[str] = None
    brock: Optional[str] = None
    returnDay: Optional[str] = None
    owner_id: Optional[int] = None
    hover_image: Optional[str] = None
    tutorial_video: Optional[str] = None
    tags: Optional[List[str]] = None
    features: Optional[List[str]] = None
    colors: Optional[List[Dict[str, Any]]] = None
    category_id: Optional[int] = None
    images: Optional[List[ProductImageSchema]] = Field(None, min_items=1, description="List of product images")

class CategoryInfo(BaseModel):
    id: int
    name: str
    slug: str
    image: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProductResponse(ProductBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryInfo] = None
    
    class Config:
        from_attributes = True

# Request schema for setting primary image
class SetPrimaryImageRequest(BaseModel):
    image_index: int = Field(..., ge=0, description="Index of the image in the images array")

class SetPrimaryImageResponse(BaseModel):
    message: str
    primary_image_index: int
    product_id: int