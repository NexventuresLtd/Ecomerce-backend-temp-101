from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
import re
from .returnLoginSchema import ReturnUser

class CreateUserRequest(BaseModel):
    """Schema for user registration request"""
    fname: str
    lname: str
    email: str
    phone: str
    password: str
    profile_pic: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "fname": "John",
                "lname": "Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "password": "SecurePass123",
                "profile_pic": "https://example.com/profile.jpg"
            }
        } 
class LoginUser(BaseModel):
    email: Optional[EmailStr]
    password: Optional[str]

class Token(BaseModel):  # token validation schema
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    UserInfo: ReturnUser

