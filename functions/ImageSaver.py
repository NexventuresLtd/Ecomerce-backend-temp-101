
# routes/product.py
import os
import shutil
from fastapi import (
    UploadFile,

)

# ---------------- CONFIG ----------------
IMAGE_FOLDER = "./static/images"
BASE_URL = "/static/images/"
os.makedirs(IMAGE_FOLDER, exist_ok=True)
# ---------------- HELPERS ----------------
def save_uploaded_file(file: UploadFile, item_id: int, index: int) -> str:
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{item_id}_{index}{ext}"
    filepath = os.path.join(IMAGE_FOLDER, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"{BASE_URL}{filename}"

