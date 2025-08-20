from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
import re
from .returnLoginSchema import ReturnUser

class CreateUserRequest(BaseModel):
    """Schema for user registration request"""
    fname: str = Field(..., min_length=1, max_length=50, 
                      description="User's first name")
    lname: str = Field(..., min_length=1, max_length=50,
                      description="User's last name")
    email: EmailStr = Field(..., description="User's email address")
    phone: str = Field(..., min_length=10, max_length=20,
                      description="User's phone number with country code")
    password: str = Field(..., min_length=8, max_length=100,
                         description="User's password")
    profile_pic: Optional[str] = Field(None,
                                     description="URL to user's profile picture")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        if not re.match(r'^\+?[0-9]{10,15}$', v):
            raise ValueError('Phone number must be 10-15 digits with optional country code')
        return v
    
    
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

