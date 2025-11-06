from fastapi import APIRouter, Depends,HTTPException, Request,BackgroundTasks,status
from fastapi.responses import HTMLResponse
from typing import Annotated
from starlette import status
from db.connection import db_dependency
from schemas.auth.schemas import CreateUserRequest, LoginUser
from dotenv import load_dotenv
from schemas.auth.RegisterResponse import AuthProvider_validator
import os

from models.userModels import Users, UserRole
from schemas.auth.schemas import CreateUserRequest

from datetime import datetime

import os

# Import from divided files
from Endpoints.Auth.normal_login import login_for_access_token, get_current_user
from Endpoints.Auth.normal_register import register_user
from Endpoints.Auth.social_login import google_auth_token
from Endpoints.Auth.social_register import sign_up_with_google
from Endpoints.Auth.SaveUserLogs import clear_logs_endpoint,get_device_history



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
    # response_model=dict,
    responses={
        status.HTTP_200_OK: {"description": "Successfully authenticated"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"description": "Account inactive"},
    }
)
async def login_route(
    request: Request,
    form_data: LoginUser,
    db: db_dependency,
    background_tasks: BackgroundTasks = BackgroundTasks()
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
    return await login_for_access_token(form_data, db, request,background_tasks)

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


@router.get("/users")
async def get_all_users(
    db: db_dependency,
    current_user: user_dependency,
    skip: int = 0,
    limit: int = 100
):
    """
    Get all users with total count (Admin only)
    """
    # Check if current user has admin privileges
    if not current_user or not current_user.get("role") == UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Get total count of users
        total_users = db.query(Users).count()
        
        # Get paginated users
        users = db.query(Users).offset(skip).limit(limit).all()
        
        # Convert users to list of dictionaries
        users_list = []
        for user in users:
            users_list.append({
                "id": user.id,
                "fname": user.fname,
                "lname": user.lname,
                "email": user.email,
                "phone": user.phone,
                "profile_pic": user.profile_pic,
                "role": user.role.value if user.role else None,
                "provider": user.provider.value if user.provider else None,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            })
        
        return {
            "message": "Users retrieved successfully",
            "users": users_list,
            "total_users": total_users,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "returned": len(users_list)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving users: {str(e)}"
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: dict,
    db: db_dependency,
    current_user: user_dependency
):
    """
    Update user data
    """
    # Check if user is updating their own data or is admin
    is_own_profile = current_user.get("user_id") == user_id
    is_admin = current_user.get("role") == UserRole.ADMIN.value
    
    if not is_own_profile and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    try:
        # Find the user
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Define allowed fields that can be updated
        allowed_fields = ["fname", "lname", "phone", "profile_pic", "is_active"]
        
        # If admin, allow more fields
        if is_admin:
            allowed_fields.extend(["role", "is_verified"])
        
        # Update allowed fields
        updated_fields = []
        for field, value in user_data.items():
            if field in allowed_fields and hasattr(user, field):
                # Handle enum fields
                if field == "role" and value:
                    user.role = UserRole(value)
                else:
                    setattr(user, field, value)
                updated_fields.append(field)
        
        # Update the timestamp
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return {
            "message": "User updated successfully",
            "updated_fields": updated_fields,
            "user": {
                "id": user.id,
                "fname": user.fname,
                "lname": user.lname,
                "email": user.email,
                "phone": user.phone,
                "profile_pic": user.profile_pic,
                "role": user.role.value if user.role else None,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data provided: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )