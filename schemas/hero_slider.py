# schemas/hero_slider.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HeroSliderBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    image: str

class HeroSliderCreate(HeroSliderBase):
    pass

class HeroSliderUpdate(HeroSliderBase):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    image: Optional[str] = None

class HeroSliderResponse(HeroSliderBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True