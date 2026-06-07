"""
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
