from datetime import timedelta
from fastapi import HTTPException, status
from db.connection import db_dependency
from models.userModels import Users
from schemas.RegisterResponse import AuthProvider_validator
from schemas.returnLoginSchema import ReturnUser
from functions.encrpt import encrypt_any_data
from .normal_login import create_access_token,create_refresh_token ,REFRESH_TOKEN_EXPIRE_DAYS
from .SaveUserLogs import save_login_log
async def google_auth_token(email: str, db: db_dependency, request):
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
            status_code=status.HTTP_401_UNAUTHORIZED,
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
    # Get client information for login log
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("User-Agent", "Unknown device")
    
    # Check if device limit is exceeded (with error handling)
    try:
        device_limit_exceeded = save_login_log(
            db=db,
            user_id=user.id,
            ip_address=ip_address,
            device_info=device_info
        )
    except Exception as e:
        # Log the error but allow login to proceed
        print(f"Warning: Failed to save login log: {str(e)}")
        device_limit_exceeded = False
    
    if device_limit_exceeded:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Multiple device login detected. Check your email for instructions to manage your devices."
        )
    # Generate access token
    token = create_access_token(
        user.email,  # Using email as identifier
        user.id,
        user.role.value if hasattr(user, 'role') else 'user',  # Handle role safely
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),  # 30 days expiration
    )
    refresh_token = create_refresh_token(
        email=user.email,
        user_id=user.id,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    # Prepare user data response
    user_info = ReturnUser.from_orm(user).dict()
    encrypted_data = encrypt_any_data({"UserInfo": user_info})
    
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "encrypted_data": encrypted_data
    }