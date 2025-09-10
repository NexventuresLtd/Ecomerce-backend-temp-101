from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class ReturnUser(BaseModel):

    email: Optional[EmailStr] = None
    provider: Optional[str] = None
    fname: Optional[str] = None
    lname: Optional[str] = None
    phone: Optional[str] = None
    profile_pic: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    two_factor: Optional[bool] = None
    role:Optional[str]=None
    created_at:Optional[datetime]=None

    class Config:
        orm_mode = True
        from_attributes = True  # Enable this to use from_orm
        json_encoders = {
            datetime: lambda v: v.isoformat()  # This ensures proper JSON serialization
        }