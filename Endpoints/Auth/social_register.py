from datetime import timedelta
from fastapi import HTTPException
from db.connection import db_dependency
from models.userModels import Users, AuthProvider, UserRole
from schemas.schemas import CreateUserRequest
from schemas.returnLoginSchema import ReturnUser
from passlib.context import CryptContext
from functions.send_mail import send_new_email
from emailsTemps.custom_email_send import custom_email
from functions.encrpt import encrypt_any_data
from .normal_login import create_access_token
from schemas.RegisterResponse import AuthProvider_validator

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def sign_up_with_google(create_user_request: CreateUserRequest, provider: AuthProvider, db: db_dependency, provider_id: str):
    """
    Handle Google sign-up/sign-in flow with the new user model.
    
    Args:
        create_user_request: User data from Google
        db: Database dependency
        provider_id: Unique identifier from Google
        avatar: URL to user's Google profile picture (optional)
    """
    # Check if user exists by provider_id (most reliable check first)
    existing_user_by_provider = db.query(Users).filter(
        Users.provider_id == provider_id
    ).first()

    if existing_user_by_provider:
        if existing_user_by_provider.provider not in  AuthProvider_validator.__members__:
            raise HTTPException(
                status_code=400,
                detail="Account already registered with different provider"
            )
        return _generate_auth_response(existing_user_by_provider)

    # Check if user exists by email
    if create_user_request.email:
        existing_user_by_email = db.query(Users).filter(
            Users.email == create_user_request.email
        ).first()

        if existing_user_by_email:
            if existing_user_by_email.provider not in AuthProvider_validator.__members__:
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered with different provider"
                )
            return _generate_auth_response(existing_user_by_email)

    # Check if phone number exists (if provided)
    if create_user_request.phone:
        existing_user_by_phone = db.query(Users).filter(
            Users.phone == create_user_request.phone
        ).first()

        if existing_user_by_phone:
            if existing_user_by_phone.provider not in AuthProvider_validator.__members__:
                raise HTTPException(
                    status_code=400,
                    detail="Phone already registered with different provider"
                )
            return _generate_auth_response(existing_user_by_phone)

    try:
        # Create new user with Google provider
        create_user_model = Users(
            fname=create_user_request.fname,
            lname=create_user_request.lname,
            email=create_user_request.email,
            profile_pic=create_user_request.profile_pic,
            phone=create_user_request.phone,
            provider=provider,
            provider_id=provider_id,
            role=UserRole.BUYER,  # Default role
            is_verified=True,     # Google-authenticated users are considered verified
            is_active=True,
        )

        db.add(create_user_model)
        db.commit()
        db.refresh(create_user_model)

        # Send welcome email
        heading = "Welcome to Nex Market!"
        sub = "Complete your onboarding for a personalized experience."
        body = "<p>Thank you for joining Nex Market via Google!</p>"
        msg = custom_email(create_user_model.fname, heading, body)
        
        if send_new_email(create_user_model.email, sub, msg):
            return _generate_auth_response(create_user_model)

    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

def _generate_auth_response(user: Users):
    """Helper function to generate authentication response for existing or new user"""
    token = create_access_token(
        user.email,
        user.id,
        user.role.value,
        timedelta(minutes=60 * 24 * 30),
    )
    user_info = ReturnUser.from_orm(user).dict()
    dat = {"UserInfo": user_info}
    data = encrypt_any_data(dat)  # Uncomment if encryption is needed
    return {"access_token": token, "token_type": "bearer", "encrypted_data": data}