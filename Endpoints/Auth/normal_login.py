from fastapi import BackgroundTasks
from datetime import timedelta, datetime
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from functools import lru_cache
from jose import jwt, JWTError
from typing import Annotated, Optional
from passlib.context import CryptContext
from db.connection import db_dependency
from models.userModels import Users, AuthProvider
from sqlalchemy import or_
from schemas.auth.schemas import LoginUser
from schemas.auth.returnLoginSchema import ReturnUser
from functions.encrpt import encrypt_any_data
from functions.send_mail import send_new_email
from emailsTemps.custom_email_send import custom_email
import os
from functions.getUserLocation import get_location_from_ip
from .SaveUserLogs import save_login_log

# Load environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
FRONTEND_URL = os.getenv("FRONTEND_URL")
# Token expiration settings
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))  # 7 days

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

# Token expiration settings - cached to avoid repeated env lookups
@lru_cache(maxsize=1)
def get_token_settings():
    return {
        "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)),
        "refresh_token_expire_days": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    }

# Cache for frequently accessed user data (optional, use with caution)
_user_cache = {}

def authenticate_user(email: str, password: str, db: db_dependency) -> Optional[Users]:
    """
    Authenticate user with email and password.
    Optimized database query with only necessary fields.
    """
    # Only select necessary columns to reduce data transfer
    user = db.query(Users.id, Users.email, Users.two_factor, Users.provider, 
                   Users.is_active, Users.is_verified, Users.fname,Users.lname,Users.phone,Users.profile_pic,Users.password_hash,Users.created_at, Users.role)\
            .filter(Users.email == email).first()
    
    if not user:
        return None
        
    # Check if user registered with LOCAL provider
    if user.provider != AuthProvider.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You didn't register with email and password. Please use your {user.provider.value} account to login."
        )
        
    if not bcrypt_context.verify(password, user.password_hash):
        return None
        
    return user

def create_access_token(email: str, user_id: int, role: str, expires_delta: timedelta) -> str:
    """Create JWT access token."""
    payload = {
        "sub": email,
        "id": user_id,
        "role": role,
        "provider": AuthProvider.LOCAL.value,
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(email: str, user_id: int, expires_delta: timedelta) -> str:
    """Create a refresh token."""
    payload = {
        "sub": email,
        "id": user_id,
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def send_login_alert_email_sync(user: Users, request: Request):
    """
    Synchronous version for background tasks
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        
        # Get location
        location = "Unknown location"
        if 'get_location_from_ip' in globals():
            try:
                location = get_location_from_ip(client_ip)
            except Exception:
                pass
        
        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = "New login detected on your account"
        msg = f"""
            We noticed a login to your account with the details below:
            <p></p>
            <ul>
            <li><strong>Login Time:</strong> {login_time}  </li>
            <li><strong>Device:</strong> {request.headers.get("User-Agent", "Unknown device")} </li> 
            <li><strong>Location:</strong> {location}  </li>
            </ul>
            <p></p>
            If this was you, no further action is required.  
            If you did not initiate this login, please secure your account immediately.

            For assistance, reach out to us at <strong>support@nexventures.net</strong>.  
            You can also manage your account directly from: {FRONTEND_URL}
        """

        message = custom_email(
            name=user.fname,
            heading=subject,
            msg=msg
        )
        
        send_new_email(user.email, subject, message)
        
    except Exception as e:
        print(f"Failed to send login alert email: {str(e)}")

async def login_for_access_token(
    form_data: LoginUser, 
    db: db_dependency,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle user login and return access token with optimized performance.
    """
    try:
        # Get token settings once
        token_settings = get_token_settings()
        
        user = authenticate_user(form_data.email, form_data.password, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Please contact support.",
            )
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is Not Verified. Please Verify Before Login.",
            )
        
        # Get client information for login log
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("User-Agent", "Unknown device")
        
        # Run device check in background if it's not critical for immediate response
        device_limit_exceeded = False
        try:
            device_limit_exceeded = save_login_log(
                db=db,
                user_id=user.id,
                ip_address=ip_address,
                device_info=device_info
            )
        except Exception as e:
            print(f"Warning: Failed to save login log: {str(e)}")
        
        if device_limit_exceeded:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="Multiple device login detected. Check your email for instructions to manage your devices."
            )
        
        # Create tokens
        token_expiry = timedelta(days=token_settings["refresh_token_expire_days"])
        token = create_access_token(
            email=user.email,
            user_id=user.id,
            role=user.role.value,
            expires_delta=token_expiry
        )
        refresh_token = create_refresh_token(
            email=user.email,
            user_id=user.id,
            expires_delta=token_expiry
        )
        
        # Add email sending to background tasks (non-blocking)
        background_tasks.add_task(send_login_alert_email_sync, user, request)
        
        # Prepare user info response
        user_info = ReturnUser.from_orm(user).dict()
        # Encrypt data (consider if this is necessary for performance)
        # encrypted_data = encrypt_any_data({"UserInfo": user_info})
        
        return {
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "encrypted_data": user_info
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login. Please try again."
        )

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> dict:
    """
    Get current authenticated user from JWT token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: int = payload.get("id")
        provider: str = payload.get("provider")
        
        if None in (email, user_id, role, provider):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
            
        return {
            "email": email,
            "user_id": user_id,
            "role": role,
            "provider": provider
        }
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please login again.",
        )