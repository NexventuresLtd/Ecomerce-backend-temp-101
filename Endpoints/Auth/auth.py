from fastapi import APIRouter, Depends,HTTPException, Request
from fastapi.responses import HTMLResponse
from typing import Annotated
from starlette import status
from db.connection import db_dependency
from schemas.schemas import CreateUserRequest, LoginUser
from dotenv import load_dotenv
from schemas.RegisterResponse import AuthProvider_validator
import os


# Import from divided files
from .normal_login import login_for_access_token, get_current_user
from .normal_register import register_user
from .social_login import google_auth_token
from .social_register import sign_up_with_google
from .SaveUserLogs import clear_logs_endpoint,get_device_history



load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Type dependencies
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/clear-devices", response_class=HTMLResponse)
async def clear_devices_page(request: Request, token: str, db: db_dependency):
    return await clear_logs_endpoint(request, token, db)

@router.post("/clear-devices", response_class=HTMLResponse)
async def clear_devices_action(request: Request, token: str, db: db_dependency):
    return await clear_logs_endpoint(request, token, db)

@router.get("/api/devices/history")
async def api_device_history(request: Request, token: str, db: db_dependency):
    return await get_device_history(request, token, db)

# Protected Registration Route
@router.post("/register")
async def register_user_route(
    db: db_dependency,
    create_user_request: CreateUserRequest
):
    return await register_user(db, create_user_request)


@router.post(
    "/login",
    summary="User login",
    description="Authenticate user with email and password",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    responses={
        status.HTTP_200_OK: {"description": "Successfully authenticated"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"description": "Account inactive"},
    }
)
async def login_route(
    request: Request,
    form_data: LoginUser,
    db: db_dependency
):
    """
    Authenticate user and return access token.
    
    Args:
        request: FastAPI request object for client info
        form_data: User login credentials (email and password)
        db: Database session
        
    Returns:
        Dictionary containing:
        - access_token: JWT token for authentication
        - token_type: Bearer token type
        - encrypted_data: Encrypted user information
    """
    return await login_for_access_token(form_data, db, request)

@router.post("/signUp-social-auth")
async def social_auth_route(
    create_user_request: CreateUserRequest,
    provider: AuthProvider_validator,  # Now we can specify which provider
    provider_id: str,       # The unique ID from the provider (Google, Facebook, etc.)
    db: db_dependency,
):
    """
    Handle social authentication (Google, Facebook, Apple, etc.)
    
    Parameters:
    - create_user_request: Basic user info (fname,lname,phone, email,password)
    - provider: The authentication provider (google, facebook)
    - provider_id: Unique identifier from the provider
    """
    if provider in AuthProvider_validator:
        return await sign_up_with_google(
            create_user_request=create_user_request,
            db=db,
            provider_id=provider_id,
            provider=provider
        )
    # Add other providers here as needed
    # elif provider == AuthProvider_validator.FACEBOOK:
    #     return await sign_up_with_facebook(...)
    
    raise HTTPException(
        status_code=400,
        detail="Unsupported authentication provider"
    )

@router.post("/signIn-social-token")
async def google_auth_token_route(
    request: Request,
    Email: str,
    db: db_dependency
):
    return await google_auth_token(Email, db, request)