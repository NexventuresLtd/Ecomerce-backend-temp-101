from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime
import enum


class UserRole(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"
    AGENT = "agent"
    ADMIN = "admin"


class AuthProvider(str, enum.Enum):
    LOCAL = "LOCAL"        # email/password
    GOOGLE = "GOOGLE"
    FACEBOOK = "FACEBOOK"
    APPLE = "APPLE"


class Users(Base):
    __tablename__ = "users"

    # Primary Identity
    id = Column(Integer, primary_key=True, index=True)

    # Basic Info
    fname = Column(String(250), nullable=True, default="")
    lname = Column(String(250), nullable=True, default="")
    email = Column(String(220), unique=True, index=True, nullable=True)
    phone = Column(String(250), unique=True, index=True, nullable=True)
    profile_pic = Column(Text, nullable=True)

    # Authentication
    password_hash = Column(Text, nullable=True)   # Only for LOCAL signup
    provider = Column(Enum(AuthProvider), default=AuthProvider.LOCAL, nullable=False)
    provider_id = Column(String(255), nullable=True, index=True)  # Google/Facebook/Apple ID

    # Role Management
    role = Column(Enum(UserRole), default=UserRole.BUYER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # email/phone verification
    two_factor = Column(Boolean, default=True)  # email/phone verification

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (expand later)
    # products = relationship("Products", back_populates="seller", cascade="all, delete", lazy="dynamic")
    # orders = relationship("Orders", back_populates="buyer", cascade="all, delete", lazy="dynamic")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role}, provider={self.provider})>"

 
class OTP(Base):
    __tablename__ = "sent_otps"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, index=True)
    otp_code = Column(String, index=True)
    verification_code = Column(String, index=True)
    purpose = Column(String, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    is_used = Column(Boolean, default=False)
    
class LoginLogs(Base):
    __tablename__ = "logs_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    login_time = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)       # IPv4/IPv6
    country = Column(String(100), nullable=True)         # e.g., Rwanda, USA
    location = Column(String(255), nullable=True)        # city or region
    device_info = Column(String(255), nullable=True)     # e.g., Chrome on Windows
    device_active = Column(Boolean, default=True)

