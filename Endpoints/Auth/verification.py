from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from db.connection import db_dependency
from models.userModels import Users
from jose import jwt, JWTError
from datetime import timedelta, datetime
import os
from schemas.schemas import Token
from functions.generateToken import create_access_token
from emailsTemps.verifyEmail import _verification_template

router = APIRouter(prefix="/auth", tags=["Authentication"])

VERIFICATION_SECRET = os.getenv("VERIFICATION_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
SECRET_KEY = os.getenv("SECRET_KEY")

@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(token: str, db: db_dependency):
    try:
        payload = jwt.decode(token, VERIFICATION_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )

        # Check if token is expired
        if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification link has expired"
            )

        # Get user from database
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # If already verified
        if user.is_verified:
            return HTMLResponse(content=_verification_template(
                title="Email Already Verified",
                message="Your email address has already been verified. You cannot verify it again.",
                button_text="Go to Homepage",
                icon="⚠️",
                color="text-yellow-500"
            ), status_code=200)

        # Mark as verified
        user.is_verified = True
        db.commit()

        # Generate access token (optional use for login flows)
        _ = create_access_token(
            user_id=user.id,
            expires_delta=timedelta(minutes=60 * 24 * 30),
            additional_claims={
                "email": user.email,
                "role": user.role.value,
                "verified": True
            }
        )

        return HTMLResponse(content=_verification_template(
            title="Email Verified Successfully",
            message="Your email has been verified. You can now access all features.",
            button_text="Go to Homepage",
            icon="✅",
            color="text-green-500"
        ), status_code=200)

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )


