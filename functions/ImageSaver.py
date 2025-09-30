import os
import base64
import re
# ---------------- CONFIG ----------------
IMAGE_FOLDER = "./static/product_images"
BASE_URL = "/static/product_images/"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ---------------- HELPERS ----------------
def decode_base64(data: str):
    if not data:
        return None
    if "," in data:
        data = data.split(",", 1)[1]
    data = re.sub(r"[^A-Za-z0-9+/=]", "", data)
    missing_padding = len(data) % 4
    if missing_padding:
        data += "=" * (4 - missing_padding)
    try:
        return base64.b64decode(data)
    except Exception:
        return None

def get_image_extension(data: bytes) -> str:
    if data.startswith(b"\xFF\xD8"):
        return "jpg"
    elif data.startswith(b"\x89PNG"):
        return "png"
    elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    elif data.startswith(b"BM"):
        return "bmp"
    else:
        return "bin"

def save_image(item_id: int, image_data: bytes) -> str:
    ext = get_image_extension(image_data)
    filename = f"{item_id}.{ext}"
    filepath = os.path.join(IMAGE_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(image_data)
    return f"{BASE_URL}{filename}"