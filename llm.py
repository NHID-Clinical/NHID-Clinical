async def call_llm(text: str) -> str:
    normalized = " ".join((text or "").lower().split())

    if "hello" in normalized:
        return "hello received"
    if "status" in normalized:
        return "system operational"
    if "create" in normalized:
        return "request received"

    return f"acknowledged: {normalized}"
