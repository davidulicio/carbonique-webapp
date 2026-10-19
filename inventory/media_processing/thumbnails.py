from io import BytesIO
from pathlib import Path
from uuid import uuid4
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

def generate_thumbnail_name(filename):
    return f"{Path(filename).stem}-{uuid4().hex}.jpg"

def generate_image_thumbnail(file):
    file.open("rb")
    try:
        with Image.open(file) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((480, 480))
            out = BytesIO()
            image.save(out, format="JPEG", quality=80)
        return ContentFile(out.getvalue())
    finally:
        file.close()

def generate_pdf_thumbnail(file):
    return None
