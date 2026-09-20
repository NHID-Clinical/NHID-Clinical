from fastapi import FastAPI, Security

# Authentication lives in its own module so it can be imported without the
# voice pipeline (and therefore without `openai`), which makes it testable.
from nhid_api_auth import get_api_key

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

# Mount the voice pipeline (this fixes /voice/process 404s for tests)
app.mount("/voice", voice_app, name="voice_pipeline")

# Include other routers
app.include_router(nhid_api_endpoints.router, dependencies=[Security(get_api_key)])
# The attestation router mints credentials, so it is protected like every
# other router here. It was previously included with no dependency at all.
app.include_router(nhid_attest.router, dependencies=[Security(get_api_key)])
app.include_router(nhid_payer.router, dependencies=[Security(get_api_key)])
app.include_router(nhid_audit_export.router, dependencies=[Security(get_api_key)])

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.4.0", "voice_pipeline": "mounted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
