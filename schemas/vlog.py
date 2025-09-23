# schemas/vlog.py
from pydantic import BaseModel
from typing import List
from datetime import datetime

class VlogBase(BaseModel):
    title: str
    description: str
    youtube_id: str
    thumbnail: str
    channel: str
    published_at: datetime
    views: int
    tags: List[str]
    category: str

class VlogCreate(VlogBase):
    pass

class VlogResponse(VlogBase):
    id: str

    class Config:
        from_attributes = True
