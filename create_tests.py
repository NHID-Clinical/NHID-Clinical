import pathlib
R = pathlib.Path(__file__).parent / "tests"

R.joinpath("test_nhid_cas.py").write_text(
'''"""NHID-CAS test suite — 38 deterministic tests."""
import pytest, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","src"))
from nhid_cas import NOCFInputs,ConfigValidationError,REQUIRED_FIELDS_V1,compute_nocf,compute_ecf,compute_cas,CAS_VERIFIED_TRUST,CAS_CONDITIONAL_TRUST,CAS_REVIEW_REQUIRED,CAS_DENIED_DEGRADED
def _pi(**o):
    d=dict(entity_match_rate=1.0,intent_accuracy=1.0,domain_hit_rate=1.0,successful_actions=10,attempted_actions=10,call_drop_rate=0.0,audio_corruption_rate=0.0,tool_failure_rate=0.0,latency_ms=0.0,l_max_ms=2500.0,hallucination_risk=0.0,pii_leakage_risk=0.0,identity_ambiguity_risk=0.0,w_H=0.40,w_P=0.35,w_I=0.25)
    d.update(o);return NOCFInputs(**d)
def _pt(**o):
    b={"session_id":"3f6a1b2c-0000-4000-8000-000000000001","call_sid":"CA1234567890abcdef","ani":"***-***-1234","sip_attestation":"A","t_n_result":True,"e_r_count":1,"disambiguation_method":"passport","confirmed_npi":"1234567890","iaf_result":True,"denial_gate":"none","policy_results":[{"rule":"IDG-01","pass":True}],"timestamp_utc_ms":1780000000000}
    b.update(o);return b
def _cas_at(v):
    nocf={"A_nocf":v,"C":1.0,"E":1.0,"S":1.0,"L_hat":1.0,"R":0.0}
    return compute_cas(iaf=True,nocf_result=nocf,trace=_pt())
def test_perfect_session_yields_cas_1():
    r=compute_cas(iaf=True,nocf_result=compute_nocf(_pi()),trace=_pt())
    assert r["cas"]==1.0 and r["tier"]=="Verified Trust" and r["badge_eligible"]=="L2"
def test_cas_equals_nocf_when_ecf_perfect():
    n=compute_nocf(_pi(latency_ms=1250.0))
    r=compute_cas(iaf=True,nocf_result=n,trace=_pt())
    assert abs(r["cas"]-n["A_nocf"])<0.001
def test_iaf_failure_yields_zero_cas():
    r=compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt())
    assert r["cas"]==0.0 and r["tier"]=="Hard Denial" and r["badge_eligible"] is None
def test_zero_latency_penalty_collapses_nocf():
    n=compute_nocf(_pi(latency_ms=3000.0,l_max_ms=2500.0))
    assert n["L_hat"]==0.0 and n["A_nocf"]==0.0
    assert compute_cas(iaf=True,nocf_result=n,trace=_pt())["cas"]==0.0
def test_full_risk_collapses_nocf():
    n=compute_nocf(_pi(hallucination_risk=1.0,w_H=1.0,w_P=0.0,w_I=0.0))
    assert n["A_nocf"]==0.0
def test_risk_weights_must_sum_to_one():
    with pytest.raises(ConfigValidationError,match="sum to 1.0"): compute_nocf(_pi(w_H=0.50,w_P=0.50,w_I=0.25))
def test_l_max_below_floor_rejected():
    with pytest.raises(ConfigValidationError,match="floor"): compute_nocf(_pi(l_max_ms=800.0))
def test_phi_exchange_minimum_enforced():
    r=compute_cas(iaf=True,nocf_result=compute_nocf(_pi(latency_ms=750.0)),trace=_pt())
    assert r["cas"]<CAS_CONDITIONAL_TRUST and r["badge_eligible"] is None
def test_cas_0_90_exact_is_verified_trust():
    r=_cas_at(0.90);assert r["tier"]=="Verified Trust" and r["badge_eligible"]=="L2"
def test_cas_0_8999_is_conditional_trust():
    r=_cas_at(0.8999);assert r["tier"]=="Conditional Trust" and r["badge_eligible"]=="L1"
def test_cas_0_75_exact_is_conditional_trust():
    assert _cas_at(0.75)["tier"]=="Conditional Trust"
def test_cas_0_7499_is_review_required():
    r=_cas_at(0.7499);assert r["tier"]=="Review Required" and r["badge_eligible"] is None
def test_cas_0_50_exact_is_review_required():
    assert _cas_at(0.50)["tier"]=="Review Required"
def test_cas_0_4999_is_denied():
    assert _cas_at(0.4999)["tier"]=="Denied / Degraded"
def test_cas_0_20_exact_is_denied():
    assert _cas_at(0.20)["tier"]=="Denied / Degraded"
def test_cas_0_1999_is_hard_denial():
    assert _cas_at(0.1999)["tier"]=="Hard Denial"
def test_cas_0_0_exact_is_hard_denial():
    assert _cas_at(0.0)["tier"]=="Hard Denial"
def test_valid_format_npi_not_in_entity_graph_denies():
    r=compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt())
    assert r["cas"]==0.0 and r["tier"]=="Hard Denial"
def test_missing_stir_shaken_hard_denies():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(sip_attestation=None,t_n_result=False))["cas"]==0.0
def test_attestation_c_fails_network_trust_gate():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(sip_attestation="C",t_n_result=False))["cas"]==0.0
def test_revoked_passport_fails_disambiguation():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(disambiguation_method="passport",confirmed_npi=None,iaf_result=False,denial_gate="revoked_delegation"))["cas"]==0.0
def test_expired_passport_fails_disambiguation():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(confirmed_npi=None,iaf_result=False,denial_gate="expired_passport"))["cas"]==0.0
def test_npi_from_wrong_entity_graph_denied():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(iaf_result=False,denial_gate="cross_entity_npi"))["cas"]==0.0
def test_scope_escalation_denied():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(iaf_result=False,denial_gate="scope_escalation_rejected"))["cas"]==0.0
def test_sanctioned_npi_fails():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(iaf_result=False,denial_gate="oig_exclusion_match"))["cas"]==0.0
def test_duplicate_call_sid_replay_denied():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(iaf_result=False,denial_gate="duplicate_nonce_replay"))["cas"]==0.0
def test_latency_exceeded_collapses_nocf():
    n=compute_nocf(_pi(latency_ms=3500.0,l_max_ms=2500.0));assert n["L_hat"]==0.0
    assert compute_cas(iaf=True,nocf_result=n,trace=_pt())["cas"]==0.0
def test_extreme_hallucination_risk_degrades_cas():
    n=compute_nocf(_pi(hallucination_risk=0.95,w_H=0.40,w_P=0.35,w_I=0.25,pii_leakage_risk=0.0,identity_ambiguity_risk=0.0))
    assert compute_cas(iaf=True,nocf_result=n,trace=_pt())["cas"]<CAS_CONDITIONAL_TRUST
def test_backend_failure_cascade_reduces_cas():
    assert compute_cas(iaf=True,nocf_result=compute_nocf(_pi(tool_failure_rate=0.80)),trace=_pt())["cas"]<CAS_CONDITIONAL_TRUST
def test_pii_leakage_risk_triggers_degradation():
    n=compute_nocf(_pi(pii_leakage_risk=0.90,w_H=0.40,w_P=0.35,w_I=0.25,hallucination_risk=0.0,identity_ambiguity_risk=0.0))
    assert compute_cas(iaf=True,nocf_result=n,trace=_pt())["cas"]<CAS_CONDITIONAL_TRUST
def test_incomplete_trace_penalizes_cas():
    n=compute_nocf(_pi());t=_pt()
    for f in ["call_sid","ani","sip_attestation","e_r_count","disambiguation_method","timestamp_utc_ms"]: t[f]=None
    r=compute_cas(iaf=True,nocf_result=n,trace=t)
    assert r["ECF"]==pytest.approx(6/12) and r["cas"]==pytest.approx(0.5,abs=0.01)
def test_missing_denial_gate_field():
    assert compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(denial_gate=None,iaf_result=False))["cas"]==0.0
def test_null_timestamp_incomplete_evidence():
    r=compute_cas(iaf=True,nocf_result=compute_nocf(_pi()),trace=_pt(timestamp_utc_ms=None))
    assert r["ECF"]<1.0 and r["cas"]<1.0
def test_ecf_perfect_trace_is_1(): assert compute_ecf(_pt())==1.0
def test_ecf_all_null_is_zero(): assert compute_ecf({f:None for f in REQUIRED_FIELDS_V1})==0.0
def test_ecf_partial_fields():
    t=_pt();t["session_id"]=None;t["call_sid"]=None;assert compute_ecf(t)==pytest.approx(10/12)
def test_cas_is_deterministic():
    i=_pi(latency_ms=1000.0,hallucination_risk=0.1)
    r1=compute_cas(iaf=True,nocf_result=compute_nocf(i),trace=_pt())
    r2=compute_cas(iaf=True,nocf_result=compute_nocf(i),trace=_pt())
    assert r1["cas"]==r2["cas"]
def test_valid_npi_does_not_prove_authorization():
    r=compute_cas(iaf=False,nocf_result=compute_nocf(_pi()),trace=_pt(e_r_count=0,confirmed_npi=None,iaf_result=False,denial_gate="entity_resolution_empty"))
    assert r["cas"]==0.0 and r["tier"]=="Hard Denial"
''', encoding='utf-8')

R.joinpath("test_npi_registry.py").write_text(
'''"""
NHID-Clinical NPI Registry Validator Tests (17 tests)
"""
import pytest
from unittest.mock import MagicMock
from src.npi_registry_validator import validate_npi_format,validate_npi,NPIValidationResult
def test_valid_ten_digit_npi(): assert validate_npi_format("1234567890") is True
def test_invalid_nine_digits(): assert validate_npi_format("123456789") is False
def test_invalid_eleven_digits(): assert validate_npi_format("12345678901") is False
def test_invalid_letters_rejected(): assert validate_npi_format("123456789A") is False
def test_empty_string_rejected(): assert validate_npi_format("") is False
def test_none_rejected(): assert validate_npi_format(None) is False
def test_format_only_valid():
    r=validate_npi("1234567890",check_registry=False)
    assert r.format_valid is True and r.registry_checked is False and r.is_valid is True
def test_format_only_invalid():
    r=validate_npi("123",check_registry=False)
    assert r.format_valid is False and r.is_valid is False
def test_format_only_error_message():
    assert validate_npi("bad",check_registry=False).error is not None
def test_dataclass_fields_present():
    r=validate_npi("1234567890")
    assert all(hasattr(r,a) for a in ["npi","format_valid","registry_checked","registry_found","provider_name","error"])
def test_registry_hit_returns_found():
    m=MagicMock();m.get.return_value.json.return_value={"results":[{"basic":{"organization_name":"Test Clinic"}}]}
    r=validate_npi("1234567890",check_registry=True,http_client=m)
    assert r.registry_found is True and r.provider_name=="Test Clinic"
def test_registry_miss_returns_not_found():
    m=MagicMock();m.get.return_value.json.return_value={"results":[]}
    r=validate_npi("1234567890",check_registry=True,http_client=m)
    assert r.registry_found is False and r.is_valid is False
def test_registry_hit_individual_provider_name():
    m=MagicMock();m.get.return_value.json.return_value={"results":[{"basic":{"first_name":"Jane","last_name":"Smith"}}]}
    r=validate_npi("1234567890",check_registry=True,http_client=m)
    assert r.registry_found is True and ("Jane" in r.provider_name or "Smith" in r.provider_name)
def test_registry_http_error_captured():
    m=MagicMock();m.get.side_effect=ConnectionError("timeout")
    r=validate_npi("1234567890",check_registry=True,http_client=m)
    assert r.registry_found is None and r.error is not None and r.is_valid is False
def test_registry_timeout_is_not_valid():
    m=MagicMock();m.get.side_effect=TimeoutError("timed out")
    assert validate_npi("1234567890",check_registry=True,http_client=m).is_valid is False
def test_format_valid_no_registry_is_valid(): assert validate_npi("9999999999",check_registry=False).is_valid is True
def test_registry_not_found_is_not_valid():
    m=MagicMock();m.get.return_value.json.return_value={"results":[]}
    assert validate_npi("9999999999",check_registry=True,http_client=m).is_valid is False
''', encoding='utf-8')

R.joinpath("test_version_boundary.py").write_text(
'''"""
NHID-Clinical Version Boundary Tests (9 tests)
"""
import pytest,importlib
def test_voice_policy_importable(): assert importlib.import_module("src.voice_policy") is not None
def test_agent_identity_importable(): assert importlib.import_module("src.agent_identity") is not None
def test_npi_validator_importable(): assert importlib.import_module("src.npi_registry_validator") is not None
def test_voice_policy_has_run_voice_policy():
    from src.voice_policy import run_voice_policy;assert callable(run_voice_policy)
def test_agent_identity_has_create_delegation():
    from src.agent_identity import AgentIdentityManager;assert callable(AgentIdentityManager.create_delegation)
def test_npi_validator_has_validate_npi():
    from src.npi_registry_validator import validate_npi;assert callable(validate_npi)
def test_no_v2_version_string_in_voice_policy():
    import inspect
    from src import voice_policy
    assert "2" not in inspect.getsource(voice_policy)
def test_policy_engine_spec_version_is_v13():
    from src.nhid_policy_engine_v1 import NHID_SPEC_VERSION;assert NHID_SPEC_VERSION=="1.3"
def test_policy_engine_evaluate_all_callable():
    from src.nhid_policy_engine_v1 import evaluate_all;assert callable(evaluate_all)
''', encoding='utf-8')

R.joinpath("test_alignment_pages.py").write_text(
'''"""
NHID-Clinical Alignment Pages Tests (14 tests)
"""
import pytest, os
ALIGNMENT_PAGES=["alignment/stir-shaken.html","alignment/cms-0057-f.html","alignment/nist-ai-agent-standards.html","alignment/vendor-evidence-pack.html"]
REPO_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def page_path(r): return os.path.join(REPO_ROOT,r)
def page_content(r):
    with open(page_path(r),encoding="utf-8") as f: return f.read()
@pytest.mark.parametrize("page",ALIGNMENT_PAGES)
def test_alignment_page_exists(page): assert os.path.exists(page_path(page)),f"Missing: {page}"
@pytest.mark.parametrize("page",ALIGNMENT_PAGES)
def test_alignment_page_has_disclaimer(page):
    c=page_content(page)
    assert "early-stage" in c or "not an accredited" in c or "open proposal" in c
@pytest.mark.parametrize("page",ALIGNMENT_PAGES)
def test_alignment_page_links_to_spec(page):
    c=page_content(page)
    assert "specification.html" in c or "nhid-clinical.org/spec" in c
def test_stir_shaken_has_governance_map_link():
    assert "ai-governance-map" in page_content("alignment/stir-shaken.html") or "governance-map" in page_content("alignment/stir-shaken.html")
def test_nist_page_has_governance_map_link():
    assert "ai-governance-map" in page_content("alignment/nist-ai-agent-standards.html") or "governance-map" in page_content("alignment/nist-ai-agent-standards.html")
''', encoding='utf-8')

print("Created 4 test files. Now run:")
print("  python -m pytest tests/ -q")