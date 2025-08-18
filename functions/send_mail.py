from fastapi import HTTPException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

NEX_USERNAME = os.getenv("NEX_USERNAME")
NEX_PASSWORD = os.getenv("NEX_PASSWORD")  # Replace with App Password
NEX_SENDER_EMAIL = os.getenv("NEX_SENDER_EMAIL")

def send_new_email(Email_to, Email_sub, Email_msg):
    msg = MIMEMultipart("alternative")
    msg['From'] = formataddr(("Nexventures Ltd", NEX_SENDER_EMAIL))
    msg['To'] = Email_to
    msg['Subject'] = Email_sub
    full_message = Email_msg
    msg.attach(MIMEText(full_message, 'html', 'utf-8'))  # Specify UTF-8 encoding

    try:
        with smtplib.SMTP('webhost.dynadot.com', 587) as server:
            server.starttls()
            server.login(NEX_USERNAME, NEX_PASSWORD)
            server.sendmail(NEX_SENDER_EMAIL, Email_to, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return True
