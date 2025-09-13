from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, Float,
    Boolean, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)

    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    discount = Column(Float, nullable=True)

    rating = Column(Float, default=0.0)
    is_new = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    reviews_count = Column(Integer, default=0)
    instock = Column(Integer, default=0)
    delivery_fee = Column(String, default="")
    brock = Column(String, default="")
    returnDay = Column(String, default="")
    warranty = Column(String, default="")

    hover_image = Column(Text, nullable=True)
    tutorial_video = Column(Text, nullable=True)

    tags = Column(JSONB, default=list)        # Example: ["electronics", "sale"]
    features = Column(JSONB, default=list)    # Example: ["waterproof", "wireless"]

    # Colors as array of objects
    colors = Column(JSONB, default=list)  
    # Example:
    # [
    #   {"name": "Red", "value": "#FF0000", "image": "red.png"},
    #   {"name": "Blue", "value": "#0000FF"}
    # ]

    # Images as array of objects
    images = Column(JSONB, default=list)  
    # Example:
    # [
    #   {"url": "image1.png", "is_primary": True},
    #   {"url": "image2.png", "is_primary": False}
    # ]

    # Relationships
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True)
    category = relationship("ProductCategory")

    # Owner (uncomment when User model is ready)
    owner_id = Column(Integer, nullable=True)
    # owner = relationship("User", back_populates="products")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
