from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
import random
import string
from db.connection import db_dependency
from models.userModels import Users, OTP
from functions.send_mail import send_new_email
from emailsTemps.custom_email_send import custom_email
from schemas.auth.emailSchemas import EmailSchema, OtpVerify
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Send Notifications and OTP"])


def generate_random_otp(length=6):
    """Generate a random OTP with mix of uppercase letters and numbers"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def generate_random_verification_code(length=8):
    """Generate a random verification code with mix of letters and numbers"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# send Otp
@router.post(
    "/send-otp/",
    description="""\
    Sends an OTP (One-Time Password) to the specified email address for verification purposes.
    ### Request Body
    Provide the following JSON object:

    ```
    {
    "purpose": "login",
    "toEmail": "user@example.com"
    }
    ```
    The Otp type can be in this Choose on of above purpose
    ```
    ["login", "email"]
    """,
)
async def send_email(details: EmailSchema, db: db_dependency):
    user = db.query(Users).filter(Users.email == details.toEmail).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email Id Not Found")

    otp_subjet = {
        "login": "NexShop - Login Verification Code",
        "email": "NexShop - Account Verification",
        "reset": "NexShop - Password Reset Code",
        "Info": "NexShop - Security Access Code",
    }
    
    otp = generate_random_otp(6)  # Generates a 6-digit alphanumeric OTP
    verification = generate_random_verification_code(8)  # Generates an 8-character verification code
    
    purpose = details.purpose
    
    # Remove existing OTPs for the user if any
    otp_user = db.query(OTP).filter(OTP.account_id == user.id).first()
    # If record exists, delete it
    if otp_user:
        db.delete(otp_user)
        db.commit()
    
    # Create and store the new OTP
    new_otp = OTP(account_id=user.id, otp_code=otp, verification_code=verification, purpose=purpose)
    db.add(new_otp)
    db.commit()
    db.refresh(new_otp)

    heading = "Welcome to NexShop!"
    sub = otp_subjet[purpose]
    
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2c3e50; text-align: center;">Ecormce Web NexShop Security Code</h2>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
            <h1 style="color: #e74c3c; font-size: 32px; letter-spacing: 3px; margin: 0;">
                {otp}
            </h1>
        </div>
        
        <p style="color: #7f8c8d; line-height: 1.6;">
            This is your verification code for <strong>{purpose}</strong> on Ecormce Web NexShop.
        </p>
        
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
            <p style="color: #856404; margin: 0;">
                ⚠️ <strong>Security Notice:</strong> Never share this code with anyone. 
                Our team will never ask for your verification code.
            </p>
        </div>
        
        <p style="color: #7f8c8d; font-size: 14px; margin-top: 20px;">
            This code will expire in 10 minutes. If you didn't request this code, 
            please ignore this email or contact our support team immediately.
        </p>
        
        <div style="border-top: 2px solid #ecf0f1; margin-top: 30px; padding-top: 20px; text-align: center;">
            <p style="color: #95a5a6; font-size: 12px;">
                Ecormce Web NexShop · Secure Shopping Experience
            </p>
        </div>
    </div>
    """
    
    msg = custom_email(user.fname, heading, body)
    if send_new_email(details.toEmail, sub, msg):
        return {"message": "Email sent successfully", "verification_Code": verification}


@router.post(
    "/verify-otp",
    summary="Verify OTP Code",
    description="""\
    This endpoint is used to verify an OTP code. Example JSON request body:
    
    ```json
    {
        "otp_code": "string",
        "verification_code": "string",
        "email": "user@example.com"
    }
    ```
    """,
)
async def verify_opt(data: OtpVerify, db: db_dependency):
    user_info = db.query(Users).filter(Users.email == data.email).first()
    if not user_info:
        raise HTTPException(status_code=404, detail="Email Id Not Found")
    
    # Make OTP verification case-insensitive
    valid_otp = db.query(OTP).filter(
        OTP.otp_code == data.otp_code.upper(),  # Convert input to uppercase for case-insensitive matching
        OTP.verification_code == data.verification_code,
        OTP.account_id == user_info.id
    ).first()
    
    if not valid_otp:
        raise HTTPException(status_code=404, detail="OTP Not found")
    
    # Check if OTP is expired
    if datetime.utcnow() - valid_otp.date > timedelta(minutes=10):
        raise HTTPException(status_code=404, detail="OTP Expired")
        
    if valid_otp.purpose == "email":
        user_info.email_confirm = True
        db.commit()
        db.refresh(user_info)
        return {"detail": "Successfully Verified"}
    
    db.delete(valid_otp)
    db.commit()
    return {"detail": "Successfully Verified"}