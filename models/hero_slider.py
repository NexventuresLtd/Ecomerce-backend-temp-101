# models/hero_slider.py
from sqlalchemy import Column, String, Text, DateTime,Integer
from sqlalchemy.sql import func

from db.database import Base

class HeroSlider(Base):
    __tablename__ = "hero_sliders"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subtitle = Column(Text, nullable=True)
    image = Column(Text, nullable=False)  # URL to the image
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<HeroSlider(id={self.id}, title={self.title})>"