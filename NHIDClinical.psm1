# NHIDClinical.psm1
# PowerShell module wrapping the hosted NHID-Clinical v1.3 conformance API.
# Built for payer IT teams who live in PowerShell.

$NHID_BASE_URL = "https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod"

function Invoke-NHIDConformanceCheck {
    <#
    .SYNOPSIS
    Evaluate a single NHID-Clinical event against the v1.3 behavioral controls
    (IDG-01, PDX-01, DBC-01, EIT-01) and return the policy decision plus CAS score.
    Uses /v1/conformance/check if $env:NHID_API_KEY is set, otherwise /v1/demo/check.
    .EXAMPLE
    Invoke-NHIDConformanceCheck -SessionId "call_123" -ActorId "agent-001" -SpeechText "What are my coverage options?" -DisclosureText "I am an automated system calling on behalf of your provider."
    #>
    param(
        [Parameter(Mandatory=$true)][string]$SessionId,
        [Parameter(Mandatory=$true)][string]$ActorId,
        [Parameter(Mandatory=$true)][string]$SpeechText,
        [Parameter(Mandatory=$false)][string]$DisclosureText = "",
        [Parameter(Mandatory=$false)][bool]$EscalationPathAvailable = $true,
        [Parameter(Mandatory=$false)][int]$TurnCount = 1
    )
    $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $body = @{
        session = @{
            turn_count                = $TurnCount
            escalation_path_available = $EscalationPathAvailable
        }
        event = @{
            event_id              = [guid]::NewGuid().ToString()
            timestamp              = $now
            session_id             = $SessionId
            request_id             = "req-$([guid]::NewGuid().ToString().Substring(0,8))"
            event_type             = "POLICY"
            actor_id               = $ActorId
            state_before           = "ACTIVE"
            state_after            = "ACTIVE"
            counterparty_type      = "human_operator"
            healthcare_governance  = @{
                disclosure_timestamp     = $now
                identity_assertion_text  = $DisclosureText
                deceptive_artifact_flags = @()
                escalation_timestamp     = $null
                escalation_outcome       = $null
                phi_accessed             = @()
            }
            input_payload = @{ speech_text = $SpeechText }
        }
    } | ConvertTo-Json -Depth 10

    if ($env:NHID_API_KEY) {
        $result = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/conformance/check" -Method POST -Body $body -ContentType "application/json" -Headers @{ "x-api-key" = $env:NHID_API_KEY }
    } else {
        $result = Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/demo/check" -Method POST -Body $body -ContentType "application/json"
    }

    if ($result.conformant) {
        Write-Host "CONFORMANT - $($result.action) [CAS $($result.cas.score) / $($result.cas.tier)]" -ForegroundColor Green
    } else {
        Write-Host "VIOLATION - $($result.action) ($($result.reason_code)) [CAS $($result.cas.score) / $($result.cas.tier)]" -ForegroundColor Red
    }
    return $result
}

function Get-NHIDVendorMetrics {
    <#
    .SYNOPSIS
    Get aggregated conformance metrics (call volume, pass rate, CAS stats) for a vendor.
    Requires $env:NHID_API_KEY.
    .EXAMPLE
    Get-NHIDVendorMetrics -VendorId "my-vendor" -Days 30
    #>
    param(
        [Parameter(Mandatory=$true)][string]$VendorId,
        [Parameter(Mandatory=$false)][int]$Days = 30
    )
    Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/vendor/metrics/summary?vendor_id=$VendorId&days=$Days" -Method GET -Headers @{ "x-api-key" = $env:NHID_API_KEY }
}

function Register-NHIDPilot {
    <#
    .SYNOPSIS
    Enroll your organization in the NHID-Clinical shadow evaluation pilot.
    .EXAMPLE
    Register-NHIDPilot -OrgName "Example Health Plan" -ContactEmail "you@example.com"
    #>
    param(
        [Parameter(Mandatory=$true)][string]$OrgName,
        [Parameter(Mandatory=$true)][string]$ContactEmail
    )
    $body = @{ org_name = $OrgName; contact_email = $ContactEmail } | ConvertTo-Json
    Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/pilot/enroll" -Method POST -Body $body -ContentType "application/json"
}

function Invoke-NHIDConformanceTestSuite {
    <#
    .SYNOPSIS
    Run the hosted NHID conformance test suite (CTS), optionally a subset of test IDs.
    .EXAMPLE
    Invoke-NHIDConformanceTestSuite
    Invoke-NHIDConformanceTestSuite -TestIds @("CTS-IDG-01-01","CTS-PDX-01-01")
    #>
    param(
        [Parameter(Mandatory=$false)][string[]]$TestIds
    )
    $body = if ($TestIds) { @{ test_ids = $TestIds } | ConvertTo-Json } else { "{}" }
    Invoke-RestMethod -Uri "$NHID_BASE_URL/v1/cts/evaluate" -Method POST -Body $body -ContentType "application/json"
}

Export-ModuleMember -Function Invoke-NHIDConformanceCheck, Get-NHIDVendorMetrics, Register-NHIDPilot, Invoke-NHIDConformanceTestSuite
