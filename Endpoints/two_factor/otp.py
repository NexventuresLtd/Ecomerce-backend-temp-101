from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
import random
from db.connection import db_dependency
from models.userModels import Users, OTP
from functions.send_mail import send_new_email
from emailsTemps.custom_email_send import custom_email
from schemas.emailSchemas import EmailSchema, OtpVerify
from datetime import datetime,timedelta
# Load environment variables from .env file
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Send Notifications and OTP"])


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
        "login": "Nova AID Login OTP Verification",
        "email": "Nova AID Account Verification Code",
        "reset": "Nova AID Account Reset Code",
        "Info": "Nova AID OTP To Grant Access To Your Info",
    }
    otp = random.randint(100000, 999999)  # Generates a 6-digit OTP
    verification = random.randint(
        1000000, 9999999
    )  # Generates a 7-digit Verification OTP
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

    heading = "Welcome to Nova AID!"
    sub = otp_subjet[purpose]
    body = f"""
   <h1>{otp}</h1>  <p>That's your OTP CODE  to Verify Your <b>{purpose}</b>. Copy the OTP and use it yourself; don't share it with anyone. It will expire after 10 minutes.</p>

    """
    msg = custom_email(user.fname,heading,body)
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
    
    valid_otp = db.query(OTP).filter(
        OTP.otp_code == data.otp_code,
        OTP.verification_code == data.verification_code,
        OTP.account_id == user_info.id
    ).first()
    if not valid_otp:
        raise HTTPException(status_code=404, detail="OTP Not found")
    # Assuming `valid_otp.date` is the timestamp from the database
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