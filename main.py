from fastapi import FastAPI, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
import os

# Import all modules
import nhid_api_endpoints
import nhid_attest
import nhid_payer
import nhid_audit_export

# Critical: Import the full voice policy + Twilio/VAPI proxy app
from app import app as voice_app

app = FastAPI(
    title="NHID-Clinical Conformance & Voice Policy API",
    description="Reference implementation - Non-Human Identity Disclosure + Voice Policy Engine",
    version="1.4.0",
    contact={"name": "Brianna Baynard", "url": "https://nhid-clinical.org"},
)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Security(_api_key_header)):
    expected = os.getenv("NHID_API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Mount the voice pipeline (this fixes /voice/process 404s for tests)
app.mount("/voice", voice_app, name="voice_pipeline")

# Include other routers
app.include_router(nhid_api_endpoints.router, dependencies=[Security(get_api_key)])
app.include_router(nhid_attest.router)
app.include_router(nhid_payer.router, dependencies=[Security(get_api_key)])
app.include_router(nhid_audit_export.router, dependencies=[Security(get_api_key)])

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.4.0", "voice_pipeline": "mounted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
