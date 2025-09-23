# models/vlog.py
from sqlalchemy import Column, String, Integer, DateTime, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from db.database import Base
import uuid

class Vlog(Base):
    __tablename__ = "vlogs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    youtube_id = Column(String, nullable=False)
    thumbnail = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    views = Column(Integer, default=0)
    tags = Column(PG_ARRAY(String), default=[])
    category = Column(String, nullable=False)
