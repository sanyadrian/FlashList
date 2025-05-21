from fastapi import APIRouter, UploadFile, File
import shutil
import os
from uuid import uuid4
from typing import List

router = APIRouter(prefix="/upload", tags=["Image Upload"])

UPLOAD_DIR = "images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_image(file: UploadFile = File(...)):
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": file_name, "message": "Image uploaded successfully"}


@router.post("/multiple")
async def upload_multiple_images(files: List[UploadFile] = File(...)):
    filenames = []
    for file in files:
        ext = file.filename.split(".")[-1]
        new_name = f"{uuid4()}.{ext}"
        path = os.path.join("uploaded_images", new_name)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        filenames.append(new_name)

    return {"filenames": filenames}