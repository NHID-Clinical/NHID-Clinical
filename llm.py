import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Lazy client: constructing OpenAI() without an API key raises, which would
# make this module unimportable in environments where the key is absent (CI).
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


async def call_llm(user_text: str) -> str:
    response = _get_client().chat.completions.create(
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
