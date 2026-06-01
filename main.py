import os
from fastapi import FastAPI, Header, Security, HTTPException
from fastapi.responses import Response
from fastapi.security.api_key import APIKeyHeader

import nhid_api_endpoints
import nhid_attest
import nhid_payer
import nhid_audit_export

app = FastAPI(
    title="NHID-Clinical API",
    description="Reference implementation for AI voice agent compliance in B2B healthcare calls.",
    version="1.3.0",
    contact={"name": "Brianna Baynard", "email": "contact@nhid-clinical.org"},
    license_info={"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def _require_api_key(key: str = Security(_api_key_header)):
    expected = os.getenv("NHID_API_KEY")
    if expected and key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

app.include_router(nhid_api_endpoints.router, dependencies=[Security(_require_api_key)])
app.include_router(nhid_attest.router)
app.include_router(nhid_payer.router, dependencies=[Security(_require_api_key)])
app.include_router(nhid_audit_export.router, dependencies=[Security(_require_api_key)])

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": "1.3.0"}


_BADGE_SVG = {
    "L1": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="20">'
        '<rect width="200" height="20" rx="3" fill="#555"/>'
        '<rect x="110" width="90" height="20" rx="3" fill="#28a745"/>'
        '<text x="55" y="14" font-family="sans-serif" font-size="11" fill="#fff" text-anchor="middle">NHID-Clinical</text>'
        '<text x="155" y="14" font-family="sans-serif" font-size="11" fill="#fff" text-anchor="middle">L1 Compliant</text>'
        '</svg>'
    ),
    "L2": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="20">'
        '<rect width="200" height="20" rx="3" fill="#555"/>'
        '<rect x="110" width="90" height="20" rx="3" fill="#0052CC"/>'
        '<text x="55" y="14" font-family="sans-serif" font-size="11" fill="#fff" text-anchor="middle">NHID-Clinical</text>'
        '<text x="155" y="14" font-family="sans-serif" font-size="11" fill="#fff" text-anchor="middle">L2 Compliant</text>'
        '</svg>'
    ),
}


@app.get("/v1/certify/badge/{agent_id}", tags=["compliance"])
def get_compliance_badge(agent_id: str, x_api_key: str = Header(default=None)):
    expected = os.getenv("NHID_API_KEY")
    tier = os.getenv("NHID_BADGE_TIER", "")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=403, detail="Valid API key required")
    if not tier or tier not in _BADGE_SVG:
        raise HTTPException(status_code=402, detail="Active paid plan required for badge endpoint")
    return Response(
        content=_BADGE_SVG[tier],
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
