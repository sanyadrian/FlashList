from fastapi import APIRouter, UploadFile, File
import shutil
import os
from uuid import uuid4
from typing import List
from app.utils.s3 import upload_file_to_s3, delete_file_from_s3

router = APIRouter(prefix="/upload", tags=["Image Upload"])

@router.post("/")
async def upload_image(file: UploadFile = File(...)):
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid4()}.{file_ext}"
    
    # Read file content
    file_content = await file.read()
    
    # Upload to S3
    url = upload_file_to_s3(file_content, file_name)
    
    return {
        "filename": file_name,
        "url": url,
        "message": "Image uploaded successfully"
    }

@router.post("/multiple")
async def upload_multiple_images(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        ext = file.filename.split(".")[-1]
        file_name = f"{uuid4()}.{ext}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3
        url = upload_file_to_s3(file_content, file_name)
        
        results.append({
            "filename": file_name,
            "url": url
        })

    return {"files": results}

@router.delete("/{filename}")
async def delete_image(filename: str):
    try:
        delete_file_from_s3(filename)
        return {"message": "Image deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))