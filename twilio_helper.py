import html


def twiml(text, gather=True):
    safe_text = html.escape((text or "").strip())

    if gather:
        return f"""
<Response>
    <Say>{safe_text}</Say>
    <Gather input="speech" action="/voice/process" method="POST"/>
</Response>
"""

    return f"""
<Response>
    <Say>{safe_text}</Say>
</Response>
"""
