import boto3
import os
from botocore.exceptions import ClientError
from fastapi import HTTPException

# S3 configuration
BUCKET_NAME = "flashlist-images"
REGION = "us-east-1"  # Change this to your S3 bucket region

def get_s3_client():
    """Get S3 client with credentials from environment variables"""
    return boto3.client(
        's3',
        region_name=REGION
    )

def upload_file_to_s3(file_data: bytes, file_name: str) -> str:
    """
    Upload a file to S3 and return the URL
    """
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=file_data,
            ContentType='image/jpeg'  # Adjust content type as needed
        )
        
        # Generate the URL for the uploaded file
        url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{file_name}"
        return url
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file to S3: {str(e)}")

def delete_file_from_s3(file_name: str):
    """
    Delete a file from S3
    """
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=BUCKET_NAME,
            Key=file_name
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file from S3: {str(e)}") 