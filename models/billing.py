# models/billing.py
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from db.database import Base
import enum
from datetime import datetime


class BillingType(enum.Enum):
    PHONE = "phone"
    CARD = "card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "Other"


class Billing(Base):
    __tablename__ = "billings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Common fields
    full_name = Column(String(255), nullable=False)
    billing_type = Column(Enum(BillingType), nullable=False)

    # Card info (only used if billing_type == CARD)
    card_number = Column(String(255), nullable=True)
    expiry_date = Column(String(255), nullable=True)
    cvv = Column(String(4), nullable=True)

    # Address info
    address = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    zip_code = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    # user = relationship("Users", back_populates="billings")
