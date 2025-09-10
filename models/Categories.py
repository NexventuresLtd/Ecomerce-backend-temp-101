from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime


class MainCategory(Base):
    __tablename__ = "main_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    image = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sub_categories = relationship("SubCategory", back_populates="main_category", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_maincategory_name", "name"),
    )


class SubCategory(Base):
    __tablename__ = "sub_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    image = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    main_category_id = Column(Integer, ForeignKey("main_categories.id", ondelete="CASCADE"), nullable=False)
    main_category = relationship("MainCategory", back_populates="sub_categories")

    product_categories = relationship("ProductCategory", back_populates="sub_category", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_subcategory_name", "name"),
    )


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    image = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sub_category_id = Column(Integer, ForeignKey("sub_categories.id", ondelete="CASCADE"), nullable=False)
    sub_category = relationship("SubCategory", back_populates="product_categories")

    __table_args__ = (
        Index("idx_productcategory_name", "name"),
    )

