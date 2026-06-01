import os
from fastapi import FastAPI, Security, HTTPException
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
