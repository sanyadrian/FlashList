import os
import base64
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/generate", tags=["AI Listing Generator"])

class ListingRequest(BaseModel):
    filename: str

@router.post("/")
async def generate_listing(data: ListingRequest):
    image_path = os.path.join("images", data.filename)

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    # Read and encode image
    with open(image_path, "rb") as img_file:
        encoded_image = base64.b64encode(img_file.read()).decode("utf-8")

    # Send to GPT-4o with vision
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You're an AI assistant helping someone sell their item online. Look at the image and write:\n"
                            "1. A product title\n"
                            "2. A product description\n"
                            "3. A suggested category\n"
                            "4. 5 relevant tags"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=600
    )

    return {
        "generated": response.choices[0].message.content
    }
