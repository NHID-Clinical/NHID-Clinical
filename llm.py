import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def call_llm(user_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a healthcare administrative assistant. Be concise."
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
    )

    return response.choices[0].message.content
