# schemas/category.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class CategoryBase(BaseModel):
    name: str
    slug: str
    image: Optional[str] = None
    description: Optional[str] = None

class MainCategoryCreate(CategoryBase):
    pass

class SubCategoryCreate(CategoryBase):
    main_category_id: int

class ProductCategoryCreate(CategoryBase):
    sub_category_id: int

class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime

class MainCategoryResponse(CategoryResponse):
    sub_categories: List["SubCategoryResponse"] = []

class SubCategoryResponse(CategoryResponse):
    main_category_id: int
    product_categories: List["ProductCategoryResponse"] = []

class ProductCategoryResponse(CategoryResponse):
    sub_category_id: int

# Update forward references
MainCategoryResponse.model_rebuild()
SubCategoryResponse.model_rebuild()