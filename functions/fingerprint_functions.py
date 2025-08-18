from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from users_micro.models.fingerprint_model import FingerprintTemplate
from users_micro.models.userModels import Users as User

def save_fingerprint_template(db: Session, user_identifier: str, template_base64: str) -> FingerprintTemplate:
    """
    Saves the fingerprint template for a user identified by either National ID or phone number.

    :param db: The database session
    :param user_identifier: The National ID or phone number of the user
    :param template_base64: The base64 encoded fingerprint template
    :return: The saved FingerprintTemplate object
    """
    # Try to find the user by National ID or phone number
    user = db.query(User).filter(
        (User.N_id == user_identifier) | (User.phone == user_identifier)
    ).first()

    if not user:
        raise Exception(f"User with identifier {user_identifier} does not exist.")
    
    fingerprint_template = FingerprintTemplate(
        user_id=user.id,
        template_base64=template_base64
    )

    db.add(fingerprint_template)
    db.commit()
    db.refresh(fingerprint_template)

    return fingerprint_template


def get_fingerprint_template(db: Session, user_identifier: str) -> FingerprintTemplate:
    """
    Gets the fingerprint template for a user identified by either National ID or phone number.

    :param db: The database session
    :param user_identifier: The National ID or phone number of the user
    :return: The FingerprintTemplate object
    """
    # Try to find the fingerprint template by National ID or phone number
    fingerprint_template = db.query(FingerprintTemplate).join(User).filter(
        (User.N_id == user_identifier) | (User.phone == user_identifier)
    ).first()

    if not fingerprint_template:
        raise Exception(f"Fingerprint template for user with identifier {user_identifier} does not exist.")
    
    return fingerprint_template
