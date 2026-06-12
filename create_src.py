import pathlib
R = pathlib.Path(__file__).parent / "src"

R.joinpath("nhid_cas.py").write_text(
'''"""NHID-CAS: Non-Human Identity Call Authorization Score
Formal scoring engine for B2B healthcare administrative voice sessions.
Author: Brianna Nicole Baynard-Malone | NIST-2025-0035-0026 | CC BY 4.0
"""
from dataclasses import dataclass
from typing import Optional
REQUIRED_FIELDS_V1=["session_id","call_sid","ani","sip_attestation","t_n_result","e_r_count","disambiguation_method","confirmed_npi","iaf_result","denial_gate","policy_results","timestamp_utc_ms"]
REQUIRED_FIELDS_V2=REQUIRED_FIELDS_V1+["logging_schema_version","revocation_check","cas_score","nocf_components","deepfake_risk_score","phi_gate_outcome"]
CAS_VERIFIED_TRUST=0.90
CAS_CONDITIONAL_TRUST=0.75
CAS_REVIEW_REQUIRED=0.50
CAS_DENIED_DEGRADED=0.20
L_MAX_MS_DEFAULT=2500.0
L_MAX_MS_FLOOR=1500.0
L_MAX_MS_CEILING=5000.0
class ConfigValidationError(ValueError): pass
@dataclass
class NOCFInputs:
    entity_match_rate:float;intent_accuracy:float;domain_hit_rate:float
    successful_actions:int;attempted_actions:int
    call_drop_rate:float;audio_corruption_rate:float;tool_failure_rate:float
    latency_ms:float
    hallucination_risk:float;pii_leakage_risk:float;identity_ambiguity_risk:float
    l_max_ms:float=L_MAX_MS_DEFAULT
    w_H:float=0.40;w_P:float=0.35;w_I:float=0.25
    def validate(self):
        weight_sum=round(self.w_H+self.w_P+self.w_I,10)
        if abs(weight_sum-1.0)>1e-9: raise ConfigValidationError(f"Risk weights must sum to 1.0, got {weight_sum}")
        if self.l_max_ms<L_MAX_MS_FLOOR: raise ConfigValidationError(f"l_max_ms {self.l_max_ms} is below minimum floor {L_MAX_MS_FLOOR}")
        if self.l_max_ms>L_MAX_MS_CEILING: raise ConfigValidationError(f"l_max_ms {self.l_max_ms} exceeds ceiling {L_MAX_MS_CEILING}")
def compute_nocf(inputs:NOCFInputs)->dict:
    inputs.validate()
    C=(inputs.entity_match_rate+inputs.intent_accuracy+inputs.domain_hit_rate)/3
    E=inputs.successful_actions/max(inputs.attempted_actions,1)
    S=1.0-(inputs.call_drop_rate+inputs.audio_corruption_rate+inputs.tool_failure_rate)/3
    L_hat=max(0.0,min(1.0,1.0-(inputs.latency_ms/inputs.l_max_ms)))
    R=inputs.w_H*inputs.hallucination_risk+inputs.w_P*inputs.pii_leakage_risk+inputs.w_I*inputs.identity_ambiguity_risk
    A_nocf=(C*E*S*L_hat)*(1.0-R)
    return {"C":round(C,6),"E":round(E,6),"S":round(S,6),"L_hat":round(L_hat,6),"R":round(R,6),"A_nocf":round(A_nocf,6)}
def compute_ecf(trace:dict,required_fields:list=None)->float:
    if required_fields is None: required_fields=REQUIRED_FIELDS_V1
    if not required_fields: return 0.0
    present=sum(1 for f in required_fields if trace.get(f) is not None)
    return round(present/len(required_fields),6)
def _tier_for_cas(cas:float)->tuple:
    if cas>=CAS_VERIFIED_TRUST: return("Verified Trust","L2")
    if cas>=CAS_CONDITIONAL_TRUST: return("Conditional Trust","L1")
    if cas>=CAS_REVIEW_REQUIRED: return("Review Required",None)
    if cas>=CAS_DENIED_DEGRADED: return("Denied / Degraded",None)
    return("Hard Denial",None)
def compute_cas(iaf:bool,nocf_result:dict,trace:dict,required_fields:list=None)->dict:
    F_IAF=1.0 if iaf else 0.0
    F_NOCF=nocf_result["A_nocf"]
    ECF=compute_ecf(trace,required_fields or REQUIRED_FIELDS_V1)
    cas=round(F_IAF*F_NOCF*ECF,4)
    tier,badge=_tier_for_cas(cas)
    return{"cas":cas,"tier":tier,"badge_eligible":badge,"F_IAF":F_IAF,"F_NOCF":round(F_NOCF,4),"ECF":round(ECF,4),"nocf_detail":nocf_result}
''', encoding='utf-8')

R.joinpath("npi_registry_validator.py").write_text(
'''"""
NHID-Clinical NPI Registry Validator
Validates NPI format and optionally checks against NPPES registry.
"""
import re
import dataclasses
from typing import Optional
NPI_PATTERN=re.compile(r\'^\d{10}$\')
NPPES_BASE_URL="https://npiregistry.cms.hhs.gov/api/?version=2.1&number="
@dataclasses.dataclass
class NPIValidationResult:
    npi:str;format_valid:bool;registry_checked:bool
    registry_found:Optional[bool];provider_name:Optional[str];error:Optional[str]
    @property
    def is_valid(self)->bool:
        if not self.format_valid: return False
        if self.registry_checked: return bool(self.registry_found)
        return True
def validate_npi_format(npi:str)->bool:
    if not isinstance(npi,str): return False
    return bool(NPI_PATTERN.match(npi))
def validate_npi(npi:str,check_registry:bool=False,http_client=None)->NPIValidationResult:
    if not validate_npi_format(npi):
        return NPIValidationResult(npi=npi,format_valid=False,registry_checked=False,registry_found=None,provider_name=None,error="NPI must be exactly 10 digits")
    if not check_registry:
        return NPIValidationResult(npi=npi,format_valid=True,registry_checked=False,registry_found=None,provider_name=None,error=None)
    try:
        url=f"{NPPES_BASE_URL}{npi}"
        response=http_client.get(url)
        data=response.json()
        results=data.get("results",[])
        if results:
            name=results[0].get("basic",{}).get("organization_name") or (f"{results[0].get(\'basic\',{}).get(\'first_name\',\'\')} {results[0].get(\'basic\',{}).get(\'last_name\',\'\')}".strip())
            return NPIValidationResult(npi=npi,format_valid=True,registry_checked=True,registry_found=True,provider_name=name or None,error=None)
        return NPIValidationResult(npi=npi,format_valid=True,registry_checked=True,registry_found=False,provider_name=None,error=None)
    except Exception as exc:
        return NPIValidationResult(npi=npi,format_valid=True,registry_checked=True,registry_found=None,provider_name=None,error=str(exc))
''', encoding='utf-8')

print("Created src/nhid_cas.py and src/npi_registry_validator.py")
print("Now run: python -m pytest tests/ -q")