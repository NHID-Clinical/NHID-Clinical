# NHIDClinical.psm1
# Official PowerShell module for NHID-Clinical v1.3
# Built for payer IT teams who live in PowerShell

$NHID_BASE_URL = "https://nhid-clinical.org"

function New-NHIDAttestation {
    <#
    .SYNOPSIS
    Generate a signed attestation proving an AI agent is authorized by a provider.
    .EXAMPLE
    New-NHIDAttestation -DelegatingNPI "1234567890" -VendorId "my-vendor"
    #>
    param(
        [Parameter(Mandatory=$true)][string]$DelegatingNPI,
        [Parameter(Mandatory=$false)][string]$VendorId = "my-vendor",
        [Parameter(Mandatory=$false)][string[]]$Scope = @("claims_inquiry","eligibility_check"),
        [Parameter(Mandatory=$false)][int]$DaysValid = 365
    )
    $body = @{
        delegating_entity = $DelegatingNPI
        authorized_actor  = $VendorId
        scope             = $Scope
        expires_at        = (Get-Date).AddDays($DaysValid).ToString("o")
    } | ConvertTo-Json
    Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/attest" -Method POST -Body $body -ContentType "application/json" -Headers @{ "X-API-Key" = $env:NHID_API_KEY }
}

function Invoke-NHIDPayerScreen {
    <#
    .SYNOPSIS
    Screen an incoming AI voice call before exchanging any data.
    Returns accept/reject/escalate decision in under 200ms.
    .EXAMPLE
    Invoke-NHIDPayerScreen -CallerNPI "1234567890" -ReferenceId "abc-123" -RequestedScope "claims_inquiry"
    #>
    param(
        [Parameter(Mandatory=$true)][string]$CallerNPI,
        [Parameter(Mandatory=$true)][string]$ReferenceId,
        [Parameter(Mandatory=$true)][string]$RequestedScope
    )
    $body = @{
        caller_npi       = $CallerNPI
        reference_id     = $ReferenceId
        requested_scope  = $RequestedScope
    } | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/payer/screen" -Method POST -Body $body -ContentType "application/json"
    if ($result.recommended_action -eq "accept") {
        Write-Host "GREEN LANE - $($result.reason)" -ForegroundColor Green
    } elseif ($result.recommended_action -eq "escalate") {
        Write-Host "ESCALATE - $($result.reason)" -ForegroundColor Yellow
    } else {
        Write-Host "REJECT - $($result.reason)" -ForegroundColor Red
    }
    return $result
}

function Test-NHIDCompliance {
    <#
    .SYNOPSIS
    Evaluate a voice transcript against NHID-Clinical disclosure and escalation rules.
    .EXAMPLE
    Test-NHIDCompliance -SessionId "call_123" -AgentId "vendor_1" -Transcript "I want to speak to a human" -DisclosureConfirmed $true
    #>
    param(
        [Parameter(Mandatory=$true)][string]$SessionId,
        [Parameter(Mandatory=$true)][string]$AgentId,
        [Parameter(Mandatory=$true)][string]$Transcript,
        [Parameter(Mandatory=$false)][bool]$DisclosureConfirmed = $false
    )
    $body = @{
        session_id           = $SessionId
        agent_id             = $AgentId
        transcript_text      = $Transcript
        disclosure_confirmed = $DisclosureConfirmed
    } | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/policy/evaluate" -Method POST -Body $body -ContentType "application/json" -Headers @{ "X-API-Key" = $env:NHID_API_KEY }
    if ($result.action -eq "allow") {
        Write-Host "COMPLIANT - $($result.reason_code)" -ForegroundColor Green
    } elseif ($result.action -eq "disclose") {
        Write-Host "DISCLOSE REQUIRED - $($result.reason_code)" -ForegroundColor Yellow
    } else {
        Write-Host "ESCALATE - $($result.reason_code)" -ForegroundColor Red
    }
    return $result
}

function Get-NHIDStateRequirements {
    <#
    .SYNOPSIS
    Get US state AI disclosure requirements mapped to NHID-Clinical rules.
    .EXAMPLE
    Get-NHIDStateRequirements
    Get-NHIDStateRequirements | ConvertTo-Json
    #>
    Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/compliance/states" -Method GET
}

function Export-NHIDAuditFHIR {
    <#
    .SYNOPSIS
    Export audit trail as HL7 FHIR AuditEvent bundle or CSV.
    .EXAMPLE
    Export-NHIDAuditFHIR -SessionId "call_123" -Format fhir
    Export-NHIDAuditFHIR -SessionId "call_123" -Format csv
    #>
    param(
        [Parameter(Mandatory=$true)][string]$SessionId,
        [Parameter(Mandatory=$false)][ValidateSet("fhir","csv")][string]$Format = "fhir"
    )
    Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/audit/export/$SessionId`?format=$Format" -Method GET
}

Export-ModuleMember -Function New-NHIDAttestation, Invoke-NHIDPayerScreen, Test-NHIDCompliance, Get-NHIDStateRequirements, Export-NHIDAuditFHIR