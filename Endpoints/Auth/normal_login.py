from datetime import timedelta, datetime
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import Annotated, Optional
from passlib.context import CryptContext
from db.connection import db_dependency
from models.userModels import Users, AuthProvider
from sqlalchemy import or_
from schemas.schemas import LoginUser
from schemas.returnLoginSchema import ReturnUser
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


def authenticate_user(email: str, password: str, db: db_dependency) -> Optional[Users]:
    """
    Authenticate user with email and password.
    
    Args:
        email: User's email address
        password: Plain text password
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
        
    Raises:
        HTTPException: If user didn't register with email/password
    """
    user = db.query(Users).filter(Users.email == email).first()
    
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
    """
    Create JWT access token.
    
    Args:
        email: User's email address
        user_id: User's database ID
        role: User's role
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    payload = {
        "sub": email,
        "id": user_id,
        "role": role,
        "provider": AuthProvider.LOCAL.value,  # Include provider in token
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(email: str, user_id: int, expires_delta: timedelta) -> str:
    """
    Create a refresh token. Contains minimal info.
    """
    payload = {
        "sub": email,
        "id": user_id,
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def send_login_alert_email(user: Users, request: Request):
    """
    Send email notification about new login.
    
    Args:
        user: The user who logged in
        request: FastAPI request object for IP detection
    """
    client_ip = request.client.host if request.client else "unknown"
    
    location = get_location_from_ip(client_ip)
    
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
            If you did not initiate this login, please secure your account immediately by resetting your password or contacting our support team.

            For assistance, reach out to us at <strong>support@nexventures.net</strong>.  
            You can also manage your account directly from: {FRONTEND_URL}

        """

    message = custom_email(
        name=user.fname,
        heading=subject,
        msg=msg
        )
    
    send_new_email(user.email, subject, message)

async def login_for_access_token(
    form_data: LoginUser, 
    db: db_dependency,
    request: Request
):
    """
    Handle user login and return access token.
    
    Args:
        form_data: Login credentials (email and password)
        db: Database session
        request: FastAPI request object
        
    Returns:
        Dictionary with access token and user info
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
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
        
        token = create_access_token(
            email=user.email,
            user_id=user.id,
            role=user.role.value,
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
        refresh_token = create_refresh_token(
            email=user.email,
            user_id=user.id,
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        try:
            await send_login_alert_email(user, request)
        except Exception as e:
            print(f"Failed to send login alert email: {str(e)}")
        
        user_info = ReturnUser.from_orm(user).dict()
        encrypted_data = encrypt_any_data({"UserInfo": user_info})
        
        return {
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "encrypted_data": encrypted_data
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error during login: {str(e)}")  # Add this for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}"
        )
async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT access token
        
    Returns:
        Dictionary with user info (email, id, role, provider)
        
    Raises:
        HTTPException: If token is invalid or expired
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
            detail=f"Authentication failed: {str(e)}",
        )