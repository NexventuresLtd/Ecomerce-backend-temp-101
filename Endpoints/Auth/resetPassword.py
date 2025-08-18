# password_reset.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from uuid import uuid4
from db.connection import db_dependency
from models.userModels import Users, AuthProvider, PasswordResetToken
from functions.send_mail import send_new_email
from emailsTemps.custom_email_send import custom_email
from passlib.context import CryptContext
import os

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
FRONTEND_URL = os.getenv("FRONTEND_URL")

# Password Reset Pages
def password_reset_request_page(message: str = "", show_form: bool = True):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Reset</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {{
                theme: {{
                    extend: {{
                        colors: {{
                            slate: {{
                                800: '#1e293b',
                            }}
                        }}
                    }}
                }}
            }}
        </script>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
            <div class="text-center mb-6">
                <h1 class="text-2xl font-bold text-slate-800">Reset Password</h1>
                <p class="text-gray-600 mt-2">Enter your email to receive a reset link</p>
            </div>
            
            {f'<div class="mb-4 p-3 bg-green-100 text-green-700 rounded">{message}</div>' if message else ''}
            
            {f'''
            <form method="POST" class="space-y-4">
                <div>
                    <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input type="email" id="email" name="email" required
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent">
                </div>
                <button type="submit" 
                    class="w-full bg-slate-800 text-white py-2 px-4 rounded-md hover:bg-slate-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-slate-800 focus:ring-offset-2">
                    Send Reset Link
                </button>
            </form>
            ''' if show_form else ''}
            
            <div class="mt-4 text-center">
                <a href="/login" class="text-slate-800 hover:underline font-medium">Back to Login</a>
            </div>
        </div>
    </body>
    </html>
    """

def password_reset_form_page(token: str, error: str = ""):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Password</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
            <div class="text-center mb-6">
                <h1 class="text-2xl font-bold text-slate-800">Create New Password</h1>
                <p class="text-gray-600 mt-2">Enter and confirm your new password</p>
            </div>
            
            {f'<div class="mb-4 p-3 bg-red-100 text-red-700 rounded">{error}</div>' if error else ''}
            
            <form method="POST" class="space-y-4">
                <input type="hidden" name="token" value="{token}">
                <div>
                    <label for="new_password" class="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                    <input type="password" id="new_password" name="new_password" required minlength="8"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent"
                        placeholder="At least 8 characters">
                </div>
                <div>
                    <label for="confirm_password" class="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                    <input type="password" id="confirm_password" name="confirm_password" required minlength="8"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent"
                        placeholder="Re-enter your password">
                </div>
                <button type="submit" 
                    class="w-full bg-slate-800 text-white py-2 px-4 rounded-md hover:bg-slate-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-slate-800 focus:ring-offset-2">
                    Reset Password
                </button>
            </form>
        </div>
    </body>
    </html>
    """

def password_reset_success_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Success</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-lg p-8 w-full max-w-md text-center">
            <div class="mb-6">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-green-500 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <h1 class="text-2xl font-bold text-slate-800 mt-4">Password Updated</h1>
                <p class="text-gray-600 mt-2">Your password has been changed successfully</p>
            </div>
            <a href="/login" 
                class="inline-block bg-slate-800 text-white py-2 px-6 rounded-md hover:bg-slate-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-slate-800 focus:ring-offset-2">
                Continue to Login
            </a>
        </div>
    </body>
    </html>
    """

# Routes
@router.post("/request-password-reset", response_class=HTMLResponse)
async def request_password_reset(
    db: db_dependency,
    request: Request,
    email: str = Form(...),
):
    user = db.query(Users).filter(Users.email == email).first()
    
    if not user:
        # Generic response for security
        return password_reset_request_page(
            message="If this email exists in our system, you'll receive a reset link",
            show_form=False
        )
    
    if user.provider != AuthProvider.LOCAL:
        return password_reset_request_page(
            message=f"Please sign in using your {user.provider.value} account",
            show_form=False
        )
    
    # Create and save reset token
    reset_token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    db.add(PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at
    ))
    db.commit()
    
    # Send reset email using your custom function
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    subject="Your Password Reset Link"
    email_content = custom_email(
        name=user.fname or user.email,
        heading="Password Reset Request",
        msg=f"""
        <p>We received a request to reset your password. Click the button below to proceed:</p>
        <a href="{reset_link}" style="display: inline-block; margin: 20px 0; padding: 12px 24px; 
            background-color: #1e293b; color: white; text-decoration: none; border-radius: 4px; 
            font-weight: bold;">Reset Password</a>
        <p>If you didn't request this, please ignore this email.</p>
        <p style="color: #64748b; font-size: 14px;">This link expires in 1 hour.</p>
        """
    )
    
    send_new_email(
        user.email,
        subject,
        email_content
    )
    
    return password_reset_request_page(
        message="Password reset link sent to your email",
        show_form=False
    )

@router.get("/reset-password", response_class=HTMLResponse)
async def show_reset_form(token: str, db: db_dependency):
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.is_used == False
    ).first()
    
    if not db_token:
        return HTMLResponse(
            content=password_reset_request_page(
                message="Invalid or expired reset link",
                show_form=True
            ),
            status_code=400
        )
    
    return password_reset_form_page(token)

@router.post("/reset-password", response_class=HTMLResponse)
async def process_password_reset(
    request: Request,
    db: db_dependency,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    # Validate token
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.is_used == False
    ).first()
    
    if not db_token:
        return HTMLResponse(
            content=password_reset_request_page(
                message="Invalid or expired reset link",
                show_form=True
            ),
            status_code=400
        )
    
    # Validate passwords
    if new_password != confirm_password:
        return password_reset_form_page(
            token,
            error="Passwords don't match"
        )
    
    if len(new_password) < 8:
        return password_reset_form_page(
            token,
            error="Password must be at least 8 characters"
        )
    
    # Update user password
    user = db.query(Users).get(db_token.user_id)
    user.password_hash = bcrypt_context.hash(new_password)
    db_token.is_used = True
    db.commit()
    
    # Send confirmation email
    subject="Your Password Has Been Changed"
    email_content = custom_email(
        name=user.fname or user.email,
        heading="Password Changed Successfully",
        msg="""
        <p>Your password has been successfully updated.</p>
        <p>If you didn't make this change, please contact our support team immediately.</p>
        """
    )
    
    send_new_email(
        user.email,
        subject,
        email_content
    )
    
    return password_reset_success_page()