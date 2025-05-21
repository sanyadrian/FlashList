from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/price", tags=["Pricing"])

class PriceRequest(BaseModel):
    title: str
    description: str

@router.post("/")
async def suggest_price(data: PriceRequest):
    prompt = (
        f"You're a pricing assistant for secondhand marketplaces like eBay and Craigslist. "
        f"Estimate a fair resale price for this item based on the title and description below. "
        f"Respond with just a number in USD — no currency symbol, no explanation.\n\n"
        f"Title: {data.title}\n"
        f"Description: {data.description}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10
    )

    return {
        "price_estimate": response.choices[0].message.content.strip()
    }
