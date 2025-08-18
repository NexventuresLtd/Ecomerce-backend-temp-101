from datetime import timedelta
from fastapi import HTTPException, status
from db.connection import db_dependency
from models.userModels import Users
from schemas.RegisterResponse import AuthProvider_validator
from schemas.returnLoginSchema import ReturnUser
from functions.encrpt import encrypt_any_data
from .normal_login import create_access_token

async def google_auth_token(email: str, db: db_dependency):
    """
    Authenticate a user via Google OAuth token and return access token.
    
    Args:
        email: User's email from Google OAuth
        db: Database dependency
        
    Returns:
        Dictionary containing access token and user information
        
    Raises:
        HTTPException: If user not found or not registered via Google
    """
    # Validate email is not empty
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for Google authentication"
        )

    # Check if user exists with this email
    user = db.query(Users).filter(Users.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with the provided Google credentials"
        )

    # Verify the user registered via Google
    if user.provider not in AuthProvider_validator.__members__:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email was not registered via Provider. Please use the original sign-in method"
        )

    # Verify the user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support"
        )

    # Generate access token
    token = create_access_token(
        user.email,  # Using email as identifier
        user.id,
        user.role.value if hasattr(user, 'role') else 'user',  # Handle role safely
        timedelta(minutes=60 * 24 * 30),  # 30 days expiration
    )

    # Prepare user data response
    user_info = ReturnUser.from_orm(user).dict()
    encrypted_data = encrypt_any_data({"UserInfo": user_info})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "encrypted_data": encrypted_data
    }