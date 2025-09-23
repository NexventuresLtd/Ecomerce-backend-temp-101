# routes/billing.py
from fastapi import APIRouter, HTTPException, status
from db.connection import db_dependency
from db.VerifyToken import user_dependency
from models.billing import Billing, BillingType

router = APIRouter(prefix="/billing", tags=["Billing"])


# ------------------ USER ENDPOINTS ------------------

@router.post("/add")
async def add_billing(
    db: db_dependency ,
    user: user_dependency ,
    full_name: str,
    billing_type: BillingType,
    card_number: str = None,
    expiry_date: str = None,
    cvv: str = None,
    address: str = None,
    city: str = None,
    zip_code: str = None,
    country: str = None,
):
    if isinstance(user, HTTPException):
        raise user

    # Ensure card details are given if type is CARD
    if billing_type == BillingType.CARD and (not card_number or not expiry_date or not cvv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card details are required for billing type CARD"
        )

    billing_entry = Billing(
        user_id=user["user_id"],
        full_name=full_name,
        billing_type=billing_type,
        card_number=card_number,
        expiry_date=expiry_date,
        cvv=cvv,
        address=address,
        city=city,
        zip_code=zip_code,
        country=country,
    )
    db.add(billing_entry)
    db.commit()
    db.refresh(billing_entry)

    return {"message": "Billing method added successfully", "billing_id": billing_entry.id}


@router.get("/my-billings")
async def view_billings(db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    View all billing methods of the current user.
    """
    billings = db.query(Billing).filter(Billing.user_id == user["user_id"]).all()
    return {"billings": billings}


@router.put("/update/{billing_id}")
async def update_billing(
    db: db_dependency ,
    user: user_dependency ,
    billing_id: int,
    full_name: str = None,
    billing_type: BillingType = None,
    card_number: str = None,
    expiry_date: str = None,
    cvv: str = None,
    address: str = None,
    city: str = None,
    zip_code: str = None,
    country: str = None,
):
    if isinstance(user, HTTPException):
        raise user

    billing = db.query(Billing).filter(
        Billing.id == billing_id,
        Billing.user_id == user["user_id"]
    ).first()

    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing method not found")

    # Update only provided fields
    if full_name: billing.full_name = full_name
    if billing_type: billing.billing_type = billing_type
    if card_number: billing.card_number = card_number
    if expiry_date: billing.expiry_date = expiry_date
    if cvv: billing.cvv = cvv
    if address: billing.address = address
    if city: billing.city = city
    if zip_code: billing.zip_code = zip_code
    if country: billing.country = country

    db.commit()
    db.refresh(billing)

    return {"message": "Billing method updated successfully", "billing": billing}


@router.delete("/delete/{billing_id}")
async def delete_billing(billing_id: int, db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    billing = db.query(Billing).filter(
        Billing.id == billing_id,
        Billing.user_id == user["user_id"]
    ).first()

    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing method not found")

    db.delete(billing)
    db.commit()
    return {"message": "Billing method deleted successfully"}


# ------------------ ADMIN ENDPOINTS ------------------

@router.get("/all")
async def get_all_billings(db: db_dependency, user: user_dependency):
    if isinstance(user, HTTPException):
        raise user

    """
    Admin: View all billing entries in the system.
    """
    billings = db.query(Billing).all()
    return {"billings": billings}
