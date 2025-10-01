# routes/category.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import  selectinload
from typing import List

from db.connection import db_dependency
from models.Categories import MainCategory, SubCategory, ProductCategory
from schemas.productManagement.category import (
    MainCategoryCreate, MainCategoryResponse,
    SubCategoryCreate, SubCategoryResponse,
    ProductCategoryCreate, ProductCategoryResponse
)

router = APIRouter(prefix="/categories", tags=["categories"])

# Main Category endpoints
@router.get("/main", response_model=List[MainCategoryResponse])
def get_main_categories(
    db: db_dependency,
    skip: int = 0, 
    limit: int = 10000, 
):
    return db.query(MainCategory).offset(skip).limit(limit).all()

@router.get("/main/{category_id}", response_model=MainCategoryResponse)
def get_main_category(category_id: int, db: db_dependency):
    category = db.query(MainCategory).filter(MainCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Main category not found")
    return category

@router.post("/main", response_model=MainCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_main_category(category: MainCategoryCreate, db: db_dependency):
    # Check if slug already exists
    if db.query(MainCategory).filter(MainCategory.slug == category.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    db_category = MainCategory(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.put("/main/{category_id}", response_model=MainCategoryResponse)
def update_main_category(
    category_id: int, 
    category: MainCategoryCreate, 
    db: db_dependency
):
    db_category = db.query(MainCategory).filter(MainCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Main category not found")
    
    for key, value in category.model_dump().items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/main/{category_id}")
def delete_main_category(category_id: int, db: db_dependency):
    db_category = db.query(MainCategory).filter(MainCategory.id == category_id).first()
    if not db_category:
        print("Main category not found", category_id)
        raise HTTPException(status_code=404, detail="Main category not found")
    
    db.delete(db_category)
    db.commit()
    return {"message": "Main category deleted successfully"}

# Sub Category endpoints
@router.get("/sub", response_model=List[SubCategoryResponse])
def get_sub_categories(
    db: db_dependency,
    skip: int = 0, 
    limit: int = 10000, 
):
    return db.query(SubCategory).offset(skip).limit(limit).all()

@router.get("/sub/{category_id}", response_model=SubCategoryResponse)
def get_sub_category(category_id: int, db: db_dependency):
    category = db.query(SubCategory).filter(SubCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Sub category not found")
    return category

@router.get("/main/{main_category_id}/sub", response_model=List[SubCategoryResponse])
def get_sub_categories_by_main_category(main_category_id: int, db: db_dependency):
    return db.query(SubCategory).filter(SubCategory.main_category_id == main_category_id).all()

@router.post("/sub", response_model=SubCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_sub_category(category: SubCategoryCreate, db: db_dependency):
    # Check if main category exists
    if not db.query(MainCategory).filter(MainCategory.id == category.main_category_id).first():
        raise HTTPException(status_code=400, detail="Main category does not exist")
    
    db_category = SubCategory(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.put("/sub/{category_id}", response_model=SubCategoryResponse)
def update_sub_category(
    category_id: int, 
    category: SubCategoryCreate, 
    db: db_dependency
):
    db_category = db.query(SubCategory).filter(SubCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Sub category not found")
    
    for key, value in category.model_dump().items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/sub/{category_id}")
def delete_sub_category(category_id: int, db: db_dependency):
    db_category = db.query(SubCategory).filter(SubCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Sub category not found")
    
    db.delete(db_category)
    db.commit()
    return {"message": "Sub category deleted successfully"}

# Product Category endpoints
@router.get("/product", response_model=List[ProductCategoryResponse])
def get_product_categories(
    db: db_dependency,
    skip: int = 0, 
    limit: int = 10000, 
):
    return db.query(ProductCategory).offset(skip).limit(limit).all()

@router.get("/product/{category_id}", response_model=ProductCategoryResponse)
def get_product_category(category_id: int, db: db_dependency):
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Product category not found")
    return category

@router.get("/sub/{sub_category_id}/product", response_model=List[ProductCategoryResponse])
def get_product_categories_by_sub_category(sub_category_id: int, db: db_dependency):
    return db.query(ProductCategory).filter(ProductCategory.sub_category_id == sub_category_id).all()

@router.post("/product", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_product_category(category: ProductCategoryCreate, db: db_dependency):
    # Check if sub category exists
    if not db.query(SubCategory).filter(SubCategory.id == category.sub_category_id).first():
        raise HTTPException(status_code=400, detail="Sub category does not exist")
    
    db_category = ProductCategory(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.put("/product/{category_id}", response_model=ProductCategoryResponse)
def update_product_category(
    category_id: int, 
    category: ProductCategoryCreate, 
    db: db_dependency
):
    db_category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Product category not found")
    
    for key, value in category.model_dump().items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/product/{category_id}")
def delete_product_category(category_id: int, db: db_dependency):
    db_category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Product category not found")
    
    db.delete(db_category)
    db.commit()
    return {"message": "Product category deleted successfully"}

# Hierarchical endpoints
@router.get("/hierarchy", response_model=List[MainCategoryResponse])
def get_full_category_hierarchy(db: db_dependency):
    return db.query(MainCategory).options(
        selectinload(MainCategory.sub_categories).selectinload(SubCategory.product_categories)
    ).all()

@router.get("/hierarchy/main/{main_category_id}", response_model=MainCategoryResponse)
def get_main_category_hierarchy(main_category_id: int, db: db_dependency):
    category = db.query(MainCategory).filter(MainCategory.id == main_category_id).options(
        selectinload(MainCategory.sub_categories).selectinload(SubCategory.product_categories)
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Main category not found")
    return category

@router.get("/hierarchy/sub/{sub_category_id}", response_model=SubCategoryResponse)
def get_sub_category_hierarchy(sub_category_id: int, db: db_dependency):
    category = db.query(SubCategory).filter(SubCategory.id == sub_category_id).options(
        selectinload(SubCategory.product_categories)
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Sub category not found")
    return category