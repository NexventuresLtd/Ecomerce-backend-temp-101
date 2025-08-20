from pydantic import BaseModel, EmailStr
from typing import Optional


class ReturnUser(BaseModel):

    email: Optional[EmailStr] = None
    fname: Optional[str] = None
    lname: Optional[str] = None
    phone: Optional[str] = None
    profile_pic: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    two_factor: Optional[bool] = None
    role:Optional[str]=None
    provider: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True  # Enable this to use from_orm