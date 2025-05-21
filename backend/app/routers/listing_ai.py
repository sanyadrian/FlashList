import os
import base64
import json
import re
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/generate", tags=["AI Listing Generator"])

class ListingRequest(BaseModel):
    filename: str

def extract_json_from_response(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None
    

@router.post("/")
async def generate_listing(data: ListingRequest):
    image_path = os.path.join("images", data.filename)

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    with open(image_path, "rb") as img_file:
        encoded_image = base64.b64encode(img_file.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You're an AI assistant helping someone sell their item online. "
                            "Look at the image and generate the following as a valid JSON object:\n\n"
                            "{\n"
                            "  \"title\": string,\n"
                            "  \"description\": string,\n"
                            "  \"category\": string,\n"
                            "  \"tags\": [string, string, string, string, string]\n"
                            "}\n\n"
                            "Only return the JSON. Do not add any extra commentary or formatting."
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

    raw = response.choices[0].message.content
    parsed_json = extract_json_from_response(raw)

    if not parsed_json:
        raise HTTPException(status_code=500, detail="AI response was not valid JSON")

    return parsed_json