# routes/vlog.py
from fastapi import APIRouter
from db.connection import db_dependency
from models.vlog import Vlog
from schemas.vlog import VlogCreate, VlogResponse
import uuid

router = APIRouter(prefix="/vlogs", tags=["Vlogs"])

@router.post("/", response_model=VlogResponse)
def create_vlog(vlog: VlogCreate, db: db_dependency):
    new_vlog = Vlog(
        id=str(uuid.uuid4()),
        **vlog.dict()
    )
    db.add(new_vlog)
    db.commit()
    db.refresh(new_vlog)
    return new_vlog

@router.get("/", response_model=list[VlogResponse])
def get_vlogs(db: db_dependency,skip: int = 0, limit: int = 20):
    return db.query(Vlog).offset(skip).limit(limit).all()

@router.get("/{vlog_id}", response_model=VlogResponse)
def get_vlog(vlog_id: str, db: db_dependency):
    vlog = db.query(Vlog).filter(Vlog.id == vlog_id).first()
    if not vlog:
        raise HTTPException(status_code=404, detail="Vlog not found")
    return vlog


# ---------------- UPDATE ----------------
@router.put("/update/{vlog_id}", response_model=VlogResponse)
def update_vlog(vlog_id: str, vlog_data: VlogCreate, db: db_dependency):
    vlog = db.query(Vlog).filter(Vlog.id == vlog_id).first()

    if not vlog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vlog not found")

    # Update fields
    for field, value in vlog_data.dict().items():
        setattr(vlog, field, value)

    db.commit()
    db.refresh(vlog)

    return vlog


# ---------------- DELETE ----------------
@router.delete("/delete/{vlog_id}")
def delete_vlog(vlog_id: str, db: db_dependency):
    vlog = db.query(Vlog).filter(Vlog.id == vlog_id).first()

    if not vlog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vlog not found")

    db.delete(vlog)
    db.commit()

    return {"message": "Vlog deleted successfully"}