from fastapi import HTTPException, status, Request
from db.connection import db_dependency
from models.userModels import Users, UserRole, AuthProvider
from schemas.schemas import CreateUserRequest, Token
from passlib.context import CryptContext
from functions.send_mail import send_new_email
from emailsTemps.custom_email_send import custom_email
from datetime import datetime, timedelta
from jose import jwt
import os
from fastapi.security import OAuth2PasswordBearer
from functions.generateToken import create_access_token

# Initialize dependencies
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

# Load environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
VERIFICATION_SECRET = os.getenv("VERIFICATION_SECRET")
FRONTEND_VERIFICATION_URL = os.getenv("FRONTEND_VERIFICATION_URL")

async def register_user(db: db_dependency, create_user_request: CreateUserRequest):
    try:
        # Check if email or phone already exists
        existing_user = db.query(Users).filter(
            (Users.email == create_user_request.email) | 
            (Users.phone == create_user_request.phone)
        ).first()

        if existing_user:
            if existing_user.email == create_user_request.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            if existing_user.phone == create_user_request.phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )

        # Create the user model
        create_user_model = Users(
            fname=create_user_request.fname,
            lname=create_user_request.lname,
            email=create_user_request.email,
            phone=create_user_request.phone,
            profile_pic=create_user_request.profile_pic,
            password_hash=bcrypt_context.hash(create_user_request.password),
            provider=AuthProvider.LOCAL,
            role=UserRole.BUYER,
            is_active=True,
            is_verified=False
        )

        db.add(create_user_model)
        db.commit()
        db.refresh(create_user_model)
        
        # Generate verification token (using your existing token generation)
        verification_token = create_access_token(
            str(create_user_model.id),
            timedelta(hours=24),
            token_type="verification"
        )
        
        # Create verification link
        verification_link = f"{FRONTEND_VERIFICATION_URL}?token={verification_token}"
        
        # Send verification email
        heading = "Verify Your Nex Market Account"
        sub = "Email Verification Required"
        body = f"""
        <p>Dear {create_user_model.fname},</p>
        <p>Thank you for registering with Nex Market!</p>
        <p>Please click the link below to verify your email address:</p>
        <p><a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px;">Verify Email</a></p>
        <p>Or copy this URL to your browser:</p>
        <p>{verification_link}</p>
        <p>This link will expire in 24 hours.</p>
        <p>If you didn't request this, please ignore this email.</p>
        """
        
        msg = custom_email(create_user_model.fname, heading, body)
        send_new_email(create_user_model.email, sub, msg)
        
        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "user_id": create_user_model.id,
            "email": create_user_model.email,
            "verification_sent": True
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

