

from jose import jwt
from datetime import timedelta
from datetime import datetime
import os
from schemas.auth.schemas import Token

VERIFICATION_SECRET = os.getenv("VERIFICATION_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
SECRET_KEY = os.getenv("SECRET_KEY")
def create_access_token(
    user_id: str, 
    expires_delta: timedelta, 
    token_type: str = "access",
    additional_claims: dict = None
):
    """Your existing token generation with verification support"""
    to_encode = {
        "sub": user_id,
        "type": token_type,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + expires_delta
    }
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(to_encode, 
                    VERIFICATION_SECRET if token_type == "verification" else SECRET_KEY, 
                    algorithm=ALGORITHM)