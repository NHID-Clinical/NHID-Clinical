"""
NHID-Clinical NPI Registry Validator
Validates NPI format and optionally checks against NPPES registry.
"""
import re
import dataclasses
from typing import Optional
NPI_PATTERN=re.compile(r'^\d{10}$')
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
            name=results[0].get("basic",{}).get("organization_name") or (f"{results[0].get('basic',{}).get('first_name','')} {results[0].get('basic',{}).get('last_name','')}".strip())
            return NPIValidationResult(npi=npi,format_valid=True,registry_checked=True,registry_found=True,provider_name=name or None,error=None)
        return NPIValidationResult(npi=npi,format_valid=True,registry_checked=True,registry_found=False,provider_name=None,error=None)
    except Exception as exc:
        return NPIValidationResult(npi=npi,format_valid=True,registry_checked=True,registry_found=None,provider_name=None,error=str(exc))
