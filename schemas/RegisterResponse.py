from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import enum

class RegisterResponse(BaseModel):
    """Response schema for user registration"""
    success: bool = Field(..., description="Whether the registration was successful")
    message: str = Field(..., description="Human-readable status message")
    user_id: Optional[int] = Field(None, description="ID of the registered user")
    email: Optional[EmailStr] = Field(None, description="Email address of the registered user")
    verification_sent: bool = Field(..., description="Whether verification email was sent")
    timestamp: datetime = Field(default_factory=datetime.utcnow, 
                              description="When the registration occurred")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Registration successful. Please check your email to verify your account.",
                "user_id": 123,
                "email": "user@example.com",
                "verification_sent": True,
                "timestamp": "2023-08-20T12:34:56.789Z"
            }
        }

class AuthProvider_validator(str, enum.Enum):   
    GOOGLE = "GOOGLE"
    FACEBOOK = "FACEBOOK"
    APPLE = "APPLE"