# Test live VAPI adapter endpoint with noncompliant scenario
# Run from repo root: .\scripts\test-vapi-live.ps1

$endpoint = "https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod/v1/adapters/vapi/check"
$scenarioPath = "tests/demo_scenarios/vapi_noncompliant.json"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Testing Live VAPI Adapter Endpoint" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Check if scenario file exists
if (-not (Test-Path $scenarioPath)) {
    Write-Host "ERROR: Scenario file not found: $scenarioPath" -ForegroundColor Red
    exit 1
}

Write-Host "Endpoint: $endpoint" -ForegroundColor Gray
Write-Host "Scenario: $scenarioPath" -ForegroundColor Gray
Write-Host ""

# Load the JSON payload
Write-Host "Loading scenario..." -ForegroundColor Yellow
$payload = Get-Content $scenarioPath | ConvertFrom-Json
Write-Host "Scenario loaded: $(($payload.messages | Measure-Object).Count) messages in call $(($payload.call.id))"
Write-Host "  - Bot (0.3s): $(($payload.messages[0]).message.Substring(0, [Math]::Min(60, ($payload.messages[0]).message.Length)))..."
Write-Host "  - User (3.1s): [PHI provided]"
Write-Host "  - Bot (5.8s): $(($payload.messages[2]).message)"
Write-Host ""

# Expected behavior
Write-Host "Expected Result:" -ForegroundColor Magenta
Write-Host "  ✓ conformant: false (rejection)" -ForegroundColor Magenta
Write-Host "  ✓ violations: IDG-01 (no early disclosure) + PDX-01 (PHI before disclosure)" -ForegroundColor Magenta
Write-Host "  ✓ action: DENY_DATA or LOG_ONLY" -ForegroundColor Magenta
Write-Host ""

# Call the endpoint
Write-Host "Calling live endpoint..." -ForegroundColor Yellow
try {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    $result = Invoke-RestMethod `
        -Uri $endpoint `
        -Method POST `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 10) `
        -TimeoutSec 30

    $stopwatch.Stop()

    Write-Host "✓ Success (${$stopwatch.ElapsedMilliseconds}ms)" -ForegroundColor Green
    Write-Host ""

    # Display response
    Write-Host "Response:" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 10 | Write-Host
    Write-Host ""

    # Validate
    Write-Host "Validation:" -ForegroundColor Cyan
    if ($result.conformant -eq $false) {
        Write-Host "✓ conformant is FALSE (correct rejection)" -ForegroundColor Green
    } else {
        Write-Host "✗ conformant is TRUE (unexpected — should reject noncompliant scenario)" -ForegroundColor Red
    }

    if ($result.violations -and $result.violations.Count -gt 0) {
        Write-Host "✓ Violations present: $(($result.violations | Measure-Object).Count) found" -ForegroundColor Green
        foreach ($v in $result.violations) {
            Write-Host "  - $($v.rule_id): $($v.description)" -ForegroundColor Gray
        }

        # Check for expected rule IDs
        $ruleIds = $result.violations | Select-Object -ExpandProperty rule_id
        if ($ruleIds -contains "IDG-01") {
            Write-Host "✓ IDG-01 (early disclosure required) present" -ForegroundColor Green
        } else {
            Write-Host "✗ IDG-01 missing from violations" -ForegroundColor Red
        }

        if ($ruleIds -contains "PDX-01") {
            Write-Host "✓ PDX-01 (PHI before disclosure) present" -ForegroundColor Green
        } else {
            Write-Host "✗ PDX-01 missing from violations" -ForegroundColor Red
        }
    } else {
        Write-Host "✗ No violations found (expected IDG-01 + PDX-01)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "Test Complete" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

} catch {
    Write-Host "✗ Error calling endpoint:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $errorBody = $_.Exception.Response | ConvertFrom-Json -ErrorAction SilentlyContinue
        Write-Host "Status: $statusCode" -ForegroundColor Red
        if ($errorBody) {
            Write-Host $errorBody | ConvertTo-Json
        }
    }
    exit 1
}
