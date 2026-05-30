# NHIDClinical PowerShell Module
# Install: Save to your PowerShell modules folder
# Usage: Import-Module NHIDClinical

$NHID_BASE_URL = "https://nhid-clinical.org"

function Invoke-NHIDPayerScreen {
    param(
        [Parameter(Mandatory=$true)][string]$CallerNPI,
        [Parameter(Mandatory=$true)][string]$ReferenceId,
        [Parameter(Mandatory=$true)][string]$RequestedScope
    )
    $body = @{
        caller_npi = $CallerNPI
        reference_id = $ReferenceId
        requested_scope = $RequestedScope
    } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/payer/screen" -Method POST -Body $body -ContentType "application/json"
    return $response
}

function Get-NHIDAttestation {
    param(
        [Parameter(Mandatory=$true)][string]$ReferenceId
    )
    $response = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/attest/verify/$ReferenceId" -Method GET
    return $response
}

function New-NHIDAttestation {
    param(
        [Parameter(Mandatory=$true)][string]$ApiKey,
        [Parameter(Mandatory=$true)][string]$DelegatingEntity,
        [Parameter(Mandatory=$true)][string]$AuthorizedActor,
        [Parameter(Mandatory=$true)][string[]]$Scope,
        [Parameter(Mandatory=$true)][string]$ExpiresAt
    )
    $body = @{
        delegating_entity = $DelegatingEntity
        authorized_actor = $AuthorizedActor
        scope = $Scope
        expires_at = $ExpiresAt
    } | ConvertTo-Json
    $headers = @{ "X-API-Key" = $ApiKey }
    $response = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/attest" -Method POST -Body $body -ContentType "application/json" -Headers $headers
    return $response
}

function Invoke-NHIDPolicyEvaluate {
    param(
        [Parameter(Mandatory=$true)][string]$ApiKey,
        [Parameter(Mandatory=$true)][string]$SessionId,
        [Parameter(Mandatory=$true)][string]$AgentId,
        [Parameter(Mandatory=$true)][string]$TranscriptText,
        [Parameter(Mandatory=$false)][bool]$DisclosureConfirmed = $false
    )
    $body = @{
        session_id = $SessionId
        agent_id = $AgentId
        transcript_text = $TranscriptText
        disclosure_confirmed = $DisclosureConfirmed
    } | ConvertTo-Json
    $headers = @{ "X-API-Key" = $ApiKey }
    $response = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/policy/evaluate" -Method POST -Body $body -ContentType "application/json" -Headers $headers
    return $response
}

function Get-NHIDStateRequirements {
    $response = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/compliance/states" -Method GET
    return $response
}

Export-ModuleMember -Function Invoke-NHIDPayerScreen, Get-NHIDAttestation, New-NHIDAttestation, Invoke-NHIDPolicyEvaluate, Get-NHIDStateRequirements