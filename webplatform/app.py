"""
NHID-Clinical unified web platform — FastAPI application.

Every route delegates to `nhid_bridge`, which wires to the EXISTING policy
engine, Lambda handler, event store, synthetic eval loop, adapters, and
identity manager. No policy logic is reimplemented here.

Pages:
  /            Dashboard          — CAS + detection + audit KPIs (payer/exec view)
  /analyzer    Transcript Analyzer— run a transcript through the real engine
  /generator   Synthetic Generator— run the real eval loop over the corpus
  /vendors     Vendor Verification— adapter checks + NHID-Auth v2 passport verify
  /audit       Audit Log          — durable events + DBC-01 human-review queue
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webplatform import nhid_bridge as bridge

_HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_HERE / "templates"))

app = FastAPI(title="NHID-Clinical Platform", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")

# Cached dashboard detection snapshot (computed lazily; refreshable).
_detection_snapshot: list[dict[str, Any]] | None = None


def _snapshot() -> list[dict[str, Any]]:
    global _detection_snapshot
    if _detection_snapshot is None:
        _detection_snapshot = bridge.generate_and_evaluate(
            sample_size=120, persist=False)["controls"]
    return _detection_snapshot


NAV = [
    {"href": "/", "label": "Dashboard"},
    {"href": "/analyzer", "label": "Transcript Analyzer"},
    {"href": "/generator", "label": "Synthetic Generator"},
    {"href": "/conformance", "label": "Conformance Suite"},
    {"href": "/vendors", "label": "Vendor Verification"},
    {"href": "/audit", "label": "Audit Log"},
]


def _page(request: Request, template: str, active: str, **ctx):
    # Starlette >=0.29 uses the request-first TemplateResponse signature.
    return templates.TemplateResponse(request, template, {
        "nav": NAV, "active": active, "versions": bridge.VERSIONS, **ctx,
    })


# ── Pages ────────────────────────────────────────────────────────────────────
@app.get("/")
def dashboard(request: Request):
    return _page(request, "dashboard.html", "/")


@app.get("/analyzer")
def analyzer(request: Request):
    scenarios = {k: v["label"] for k, v in bridge.DEMO_SCENARIOS.items()}
    return _page(request, "analyzer.html", "/analyzer", scenarios=scenarios)


@app.get("/generator")
def generator(request: Request):
    return _page(request, "generator.html", "/generator")


@app.get("/conformance")
def conformance(request: Request):
    return _page(request, "conformance.html", "/conformance")


@app.get("/vendors")
def vendors(request: Request):
    return _page(request, "vendors.html", "/vendors", adapters=bridge.ADAPTERS)


@app.get("/audit")
def audit(request: Request):
    return _page(request, "audit.html", "/audit")


# ── JSON API ─────────────────────────────────────────────────────────────────
@app.get("/api/health")
def api_health():
    return bridge.health()


@app.get("/api/dashboard")
def api_dashboard():
    return {
        "counts": bridge.store_counts(),
        "detection": _snapshot(),
        "cas_tiers": bridge.cas_tier_distribution(),
        "cas_thresholds": bridge.CAS_THRESHOLDS,
        "versions": bridge.VERSIONS,
    }


@app.post("/api/dashboard/refresh")
def api_dashboard_refresh():
    global _detection_snapshot
    _detection_snapshot = None
    return {"detection": _snapshot()}


@app.get("/api/scenarios")
def api_scenarios():
    return {k: {"label": v["label"], "conversation_id": v["conversation_id"],
                "turns": v["turns"]}
            for k, v in bridge.DEMO_SCENARIOS.items()}


@app.post("/api/analyze")
async def api_analyze(request: Request):
    body = await request.json()
    scenario = body.get("scenario")
    if scenario:
        sc = bridge.DEMO_SCENARIOS.get(scenario)
        if not sc:
            return JSONResponse({"error": f"unknown scenario '{scenario}'"}, 400)
        return bridge.analyze_turns(sc["conversation_id"], sc["turns"], persist=True)

    turns = body.get("turns")
    if not isinstance(turns, list) or not turns:
        return JSONResponse(
            {"error": "provide 'scenario' or a non-empty 'turns' list"}, 400)
    conversation_id = body.get("conversation_id", "web-analysis")
    return bridge.analyze_turns(conversation_id, turns, persist=True)


@app.post("/api/generate")
async def api_generate(request: Request):
    body = await request.json()
    size = int(body.get("sample_size", 100))
    persist = bool(body.get("persist", True))
    result = bridge.generate_and_evaluate(sample_size=size, persist=persist)
    # Keep the dashboard snapshot in sync with the latest run.
    global _detection_snapshot
    _detection_snapshot = result["controls"]
    return result


@app.get("/api/confusion")
def api_confusion(sample_size: int = 550):
    return bridge.confusion_matrix(sample_size)


@app.get("/api/cts")
def api_cts():
    return bridge.run_cts()


@app.post("/api/verify/passport")
async def api_verify_passport(request: Request):
    body = await request.json()
    if body.get("mode") == "supplied" and body.get("passport"):
        return bridge.verify_passport_body(body["passport"])
    # Default: mint a real demo passport (optionally tampered) and verify it.
    return bridge.mint_demo_passport(tamper=bool(body.get("tamper", False)))


@app.post("/api/adapters/{vendor}/check")
async def api_adapter_check(vendor: str, request: Request):
    payload = await request.json()
    return bridge.adapter_check(vendor, payload)


@app.get("/api/audit/events")
def api_audit_events(limit: int = 50):
    return {"events": bridge.recent_events(limit)}


@app.get("/api/audit/reviews")
def api_audit_reviews():
    return {"reviews": bridge.pending_reviews()}


@app.post("/api/audit/reviews/{queue_id}/resolve")
async def api_resolve_review(queue_id: int, request: Request):
    body = await request.json()
    disposition = body.get("disposition", "false_positive")
    if disposition not in ("confirmed_impersonation", "false_positive"):
        return JSONResponse({"error": "invalid disposition"}, 400)
    try:
        return bridge.resolve_review(
            queue_id, disposition,
            reviewer=body.get("reviewer", "web-operator"),
            notes=body.get("notes", ""))
    except Exception as exc:  # already-resolved / unknown id
        return JSONResponse({"error": str(exc)}, 400)
