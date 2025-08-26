from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Form, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, distinct
import os
from db.connection import db_dependency
from models.userModels import LoginLogs, Users
from functions.send_mail import send_new_email
from functions.generateToken import create_access_token
from emailsTemps.custom_email_send import custom_email
from jose import JWTError, jwt
from typing import Optional, List
import re
import time
from functools import lru_cache
import asyncio

# Load environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
VERIFICATION_SECRET = os.getenv("VERIFICATION_SECRET")
FRONTEND_VERIFICATION_URL = os.getenv("FRONTEND_VERIFICATION_URL")
FRONTEND_URL = os.getenv("FRONTEND_URL")
MAX_DEVICES = int(os.getenv("MAX_DEVICES", 2))  # Convert to int once

# Pre-compile regex patterns for better performance
BROWSER_PATTERN = re.compile(r'(Chrome|Firefox|Safari|Edge|Opera)[/\s](\d+\.\d+)')
OS_PATTERN = re.compile(r'(Windows NT|Linux|Mac OS X|iPhone|Android)')

@lru_cache(maxsize=1000)
def extract_browser_info(user_agent: str) -> str:
    """Cached browser and OS extraction from User-Agent string"""
    try:
        browser_match = BROWSER_PATTERN.search(user_agent)
        browser_info = browser_match.group(0) if browser_match else "Unknown Browser"
        
        os_match = OS_PATTERN.search(user_agent)
        os_info = os_match.group(1) if os_match else "Unknown OS"
        
        return f"{browser_info} on {os_info}"
    except:
        return user_agent

def generate_device_fingerprint(device_info: str, ip_address: Optional[str] = None) -> str:
    """Generate a device fingerprint based on browser/device characteristics"""
    browser_os = extract_browser_info(device_info)
    return f"device:{browser_os}"

async def send_notification_async(db: Session, user_id: int, device_count: int, max_devices: int):
    """Async function to send notification email"""
    try:
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            return
        
        clear_token = create_access_token(
            user_id=str(user_id),
            expires_delta=timedelta(hours=1),
            token_type="verification",
            additional_claims={"action": "clear_logs"}
        )
        
        clear_link = f"{FRONTEND_URL}/clear-devices?token={clear_token}"
        subject = "Suspicious Login Activity Detected"
        
        email_content = custom_email(
            name=user.fname or user.email,
            heading="Multiple Device Login Detected",
            msg=f"""
            <p>We noticed your account was accessed from {device_count} different devices (max allowed: {max_devices}).</p>
            <p>If this was you, you can review and manage your active devices:</p>
            <a href="{clear_link}" style="display: inline-block; margin: 20px 0; padding: 12px 24px; 
                background-color: #1e293b; color: white; text-decoration: none; border-radius: 4px; 
                font-weight: bold;">Review Active Devices</a>
            <p>If you don't recognize this activity, we recommend resetting your password immediately.</p>
            <p style="color: #64748b; font-size: 14px;">This link expires in 1 hour.</p>
            """
        )
        
        # Use background task or async email sending
        await asyncio.to_thread(send_new_email, user.email, subject, email_content)
        
    except Exception as e:
        print(f"Error sending notification: {str(e)}")

def save_login_log(
    db: Session,
    user_id: int,
    ip_address: str = None,
    country: str = None,
    location: str = None,
    device_info: str = None,
) -> bool:
    """
    Optimized version: Save user login activity and check device limits.
    """
    try:
        start_time = time.time()
        
        device_fingerprint = generate_device_fingerprint(device_info, ip_address)
        
        # 1. Check for existing device in single query
        existing_log = db.query(LoginLogs).filter(
            LoginLogs.user_id == user_id,
            LoginLogs.device_info == device_info,
            LoginLogs.device_active == True
        ).first()

        is_existing_device = False
        
        if existing_log:
            # Update existing log
            existing_log.login_time = datetime.utcnow()
            existing_log.ip_address = ip_address or existing_log.ip_address
            existing_log.country = country or existing_log.country
            existing_log.location = location or existing_log.location
            is_existing_device = True
        else:
            # Check for similar devices using fingerprint (optional, can be removed if not needed)
            similar_device = db.query(LoginLogs).filter(
                LoginLogs.user_id == user_id,
                LoginLogs.device_active == True,
                LoginLogs.device_info.ilike(f"%{extract_browser_info(device_info).split(' on ')[0]}%")
            ).first()
            
            if similar_device:
                # Update the similar device
                similar_device.login_time = datetime.utcnow()
                similar_device.ip_address = ip_address
                similar_device.country = country
                similar_device.location = location
                similar_device.device_info = device_info  # Update with current device info
                is_existing_device = True
            else:
                # Create new log entry
                new_log = LoginLogs(
                    user_id=user_id,
                    login_time=datetime.utcnow(),
                    ip_address=ip_address,
                    country=country,
                    location=location,
                    device_info=device_info,
                    device_active=True,
                )
                db.add(new_log)
        
        db.commit()
        
        # 2. Count unique active devices using optimized database query
        unique_devices_count = db.query(
            func.count(distinct(LoginLogs.device_info))
        ).filter(
            LoginLogs.user_id == user_id,
            LoginLogs.device_active == True,
            LoginLogs.login_time >= datetime.utcnow() - timedelta(days=30)
        ).scalar()  # Returns a single count value
        
        device_limit_exceeded = unique_devices_count > MAX_DEVICES
        
        # 3. Only send email if limit exceeded (async)
        if device_limit_exceeded:
            # Use asyncio to run email sending in background
            asyncio.create_task(send_notification_async(db, user_id, unique_devices_count, MAX_DEVICES))
        
        end_time = time.time()
        print(f"save_login_log completed in {end_time - start_time:.3f}s, devices: {unique_devices_count}")
        
        return device_limit_exceeded
        
    except Exception as e:
        print(f"Error in save_login_log: {str(e)}")
        db.rollback()
        return False

def deactivate_login_logs(db: Session, user_id: int, keep_recent: bool = True):
    """Optimized deactivation of login logs"""
    try:
        if keep_recent:
            # Get the most recent log ID in a single query
            recent_log_id = db.query(LoginLogs.id).filter(
                LoginLogs.user_id == user_id
            ).order_by(LoginLogs.login_time.desc()).limit(1).scalar()
            
            if recent_log_id:
                # Bulk update all except the most recent
                db.query(LoginLogs).filter(
                    LoginLogs.user_id == user_id,
                    LoginLogs.id != recent_log_id
                ).update({"device_active": False}, synchronize_session=False)
            else:
                db.query(LoginLogs).filter(
                    LoginLogs.user_id == user_id
                ).update({"device_active": False}, synchronize_session=False)
        else:
            # Bulk deactivate all logs
            db.query(LoginLogs).filter(
                LoginLogs.user_id == user_id
            ).update({"device_active": False}, synchronize_session=False)
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Error in deactivate_login_logs: {str(e)}")
        return False

def get_user_login_history(db: Session, user_id: int, active_only: bool = False, limit: int = 50):
    """Get user login history with limits and optimized query"""
    query = db.query(LoginLogs).filter(LoginLogs.user_id == user_id)
    
    if active_only:
        query = query.filter(LoginLogs.device_active == True)
    
    return query.order_by(LoginLogs.login_time.desc()).limit(limit).all()

def verify_clear_token(token: str):
    """Verify the clear logs token"""
    try:
        payload = jwt.decode(token, VERIFICATION_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "verification" or payload.get("action") != "clear_logs":
            raise HTTPException(status_code=400, detail="Invalid token purpose")
        return int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

def generate_password_reset_token(user_id: int):
    """Generate a password reset token"""
    return create_access_token(
        user_id=str(user_id),
        expires_delta=timedelta(hours=1),
        token_type="verification",
        additional_claims={"action": "reset_password"}
    )

# HTML Templates (unchanged, but consider moving to separate files)
clear_logs_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Management - Security Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: '#1e293b',
                    }
                }
            }
        }
    </script>
    <style>
        .device-card {
            transition: all 0.3s ease;
        }
        .device-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        }
    </style>
</head>
<body class="bg-slate-800 min-h-screen py-8 px-4">
    <div class="max-w-4xl mx-auto">
        <div class="bg-white rounded-xl shadow-2xl p-6 md:p-8 mb-6">
            <div class="text-center mb-6">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-full mb-4">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                </div>
                <h1 class="text-2xl font-bold text-slate-800">Device Management</h1>
                <p class="text-slate-600 mt-2">Manage your account's active sessions and view login history</p>
            </div>
            
            <div class="bg-slate-100 p-4 rounded-lg mb-6">
                <p class="text-slate-700 text-sm">We've detected login activity from multiple devices. For your security, you can manage your active sessions below.</p>
            </div>
            
            <form method="POST" class="space-y-4">
                <div>
                    <button type="submit" name="action" value="clear" 
                        class="w-full bg-primary hover:bg-slate-900 text-white font-medium py-3 px-4 rounded-lg transition duration-200 flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                        Deactivate All Other Sessions leave the lastest
                    </button>
                </div>
                
                <div class="">
                    <button type="submit" name="action" value="reset" 
                        class="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-4 rounded-lg transition duration-200 flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                        Deactivate All
                    </button>
                </div>
            </form>
        </div>

        <div class="bg-white rounded-xl shadow-2xl p-6 md:p-8">
            <h2 class="text-xl font-bold text-slate-800 mb-4 flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Login History (Last 30 Days)
            </h2>
            
            <div class="space-y-4" id="devices-list">
                <!-- Devices will be loaded here by JavaScript -->
            </div>
            
            <div class="mt-6 text-center">
                <button onclick="loadDevices()" class="text-primary hover:text-slate-900 font-medium flex items-center justify-center mx-auto">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh Devices
                </button>
            </div>
        </div>
    </div>

    <script>
        async function loadDevices() {
            try {
                const response = await fetch('api/devices/history?token={{token}}');
                const devices = await response.json();
                
                const devicesList = document.getElementById('devices-list');
                devicesList.innerHTML = '';
                
                if (devices.length === 0) {
                    devicesList.innerHTML = `
                        <div class="text-center py-8 text-slate-500">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p>No login history found.</p>
                        </div>
                    `;
                    return;
                }
                
                devices.forEach(device => {
                    const date = new Date(device.login_time);
                    const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                    
                    const deviceCard = document.createElement('div');
                    deviceCard.className = `device-card bg-slate-50 rounded-lg p-4 ${device.device_active ? 'border-l-4 border-primary' : 'border-l-4 border-slate-300'}`;
                    deviceCard.innerHTML = `
                        <div class="flex justify-between items-start">
                            <div>
                                <h3 class="font-medium text-slate-800">${device.device_info || 'Unknown Device'}</h3>
                                <p class="text-sm text-slate-600 mt-1">${device.ip_address || 'No IP data'} • ${device.location || 'Unknown location'}</p>
                                <p class="text-sm text-slate-500 mt-1">${formattedDate}</p>
                            </div>
                            <span class="px-2 py-1 text-xs rounded-full ${device.device_active ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-800'}">
                                ${device.device_active ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                    `;
                    devicesList.appendChild(deviceCard);
                });
            } catch (error) {
                console.error('Error loading devices:', error);
                document.getElementById('devices-list').innerHTML = `
                    <div class="text-center py-8 text-red-500">
                        <p>Error loading devices. Please try again.</p>
                    </div>
                `;
            }
        }
        
        // Load devices when page loads
        document.addEventListener('DOMContentLoaded', loadDevices);
    </script>
</body>
</html>
"""

success_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Success - Security Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-800 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-2xl p-6 md:p-8 max-w-md w-full">
        <div class="text-center">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
            </div>
            <h2 class="text-xl font-bold text-slate-800 mt-4">Success!</h2>
            <p class="text-slate-600 mt-2">{message}</p>
            <a href="{login_url}" class="mt-4 inline-block bg-primary hover:bg-slate-900 text-white font-medium py-2 px-4 rounded-lg transition duration-200">
                Return to Login
            </a>
        </div>
    </div>
</body>
</html>
"""

email_sent_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Check Your Email - Security Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-800 min极-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-2xl p-6 md:p-8 max-w-md w-full">
        <div class="text-center">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-blue-600极" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V极a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
            </div>
            <h2 class="text-xl font-bold text-slate-800 mt-4">Check Your Email</h2>
            <p class="text-slate-600 mt-2">We've sent a password reset link to your email address. Please check your inbox.</p>
        </div>
    </div>
</body>
</html>
"""

async def clear_logs_endpoint(request: Request, token: str, db: db_dependency):
    """Endpoint for clearing login logs and optional password reset"""
    try:
        user_id = verify_clear_token(token)
    except HTTPException:
        error_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error - Security Center</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-800 min-h-screen flex items-center justify-center p-4">
            <div class="bg-white rounded-xl shadow-2xl p-6 md:p-8极 max-w-md w-full">
                <div class="text-center">
                    <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </div>
                    <h2 class="text-xl font-bold text-slate-800 mt-4">Invalid or Expired Link</h2>
                    <p class="text-slate-600 mt-2">This security link is invalid or has expired. Please request a new one.</p>
                    <a href="/login" class="mt-4 inline-block bg-primary hover:bg-slate-900 text-white font-medium py-2 px-4 rounded-lg transition duration-200">
                        Return to Login
                    </a>
                </div>
            </极>
        </body>
        </html>
        """
        return HTMLResponse(error_html)
    
    if request.method == "GET":
        html_content = clear_logs_template.replace("{{token}}", token)
        return HTMLResponse(html_content)
    
    form_data = await request.form()
    action = form_data.get("action")
    
    if action == "clear":
        deactivate_login_logs(db, user_id, keep_recent=True)
        success_html = success_template.format(
            message="All other login sessions have been deactivated successfully.",
            login_url=f"{FRONTEND_URL}/login"
        )
        return HTMLResponse(success_html)
    
    elif action == "reset":
        deactivate_login_logs(db, user_id, keep_recent=False)
        reset_token = generate_password_reset_token(user_id)
        
        user = db.query(Users).filter(Users.id == user_id).first()
        if user:
            reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
            subject = "Password Reset Request"
            email_content = custom_email(
                name=user.fname or user.email,
                heading="Password Reset Request",
                msg=f"""
                <p>As requested, here's your password reset link:</p>
                <a href="{reset_link}" style="display: inline-block; margin: 20px 0; padding: 12px 24px; 
                    background-color: #1e293b; color: white; text-decoration: none; border-radius: 4px; 
                    font-weight: bold;">Reset Password</a>
                <p>If you didn't request this, please secure your account immediately.</p>
                <p style="color: #64748b; font-size: 14px;">This link expires in 1 hour.</p>
                """
            )
            
            # Send email asynchronously
            asyncio.create_task(asyncio.to_thread(send_new_email, user.email, subject, email_content))
        
        return HTMLResponse(email_sent_template)
    
    html_content = clear_logs_template.replace("{{token}}", token)
    return HTMLResponse(html_content)

async def get_device_history(request: Request, token: str, db: db_dependency):
    """API endpoint to get user's device login history with limits"""
    try:
        user_id = verify_clear_token(token)
        devices = get_user_login_history(db, user_id, limit=50)
        
        device_list = []
        for device in devices:
            device_list.append({
                "id": device.id,
                "login_time": device.login_time.isoformat(),
                "ip_address": device.ip_address,
                "country": device.country,
                "location": device.location,
                "device_info": device.device_info,
                "device_active": device.device_active
            })
        
        return JSONResponse(device_list)
    except HTTPException:
        return JSONResponse({"error": "Invalid token"}, status_code=401)