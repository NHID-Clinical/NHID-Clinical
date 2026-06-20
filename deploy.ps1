<#
.SYNOPSIS
    Windows PowerShell equivalent of `make deploy` for the NHID Clinical demo API.

.DESCRIPTION
    `make` does not exist on Windows, so this script mirrors the `deploy` target
    in the Makefile: it runs `sam build` then `sam deploy` with the same flags,
    forwarding the website-demo-feature secrets as CloudFormation
    --parameter-overrides. Empty/unset secrets are fine — the matching
    template.yaml Parameters all default to "" — so a first, secret-less deploy
    works too. On success it prints the stack's ApiBaseUrl, which the Twilio and
    ElevenLabs webhook configuration both need.

.EXAMPLE
    .\deploy.ps1 `
      -CloudflareTurnstileSecret "0x4AAA..." `
      -ElevenLabsApiKey "sk_..." `
      -ElevenLabsPhoneNumberId "phnum_1801kttwq450ewrsm1qzhe110zj6"

.EXAMPLE
    # Baseline deploy with no secrets (just stand the stack up):
    .\deploy.ps1
#>
[CmdletBinding()]
param(
    [string]$StackName = "nhid-clinical-api",
    [string]$Region    = "us-east-1",
    # Named AwsProfile (not Profile) to avoid shadowing PowerShell's automatic
    # $PROFILE variable. Forwarded as `--profile` when set.
    [string]$AwsProfile = "",

    # Website demo feature secrets (NOT the governance framework). Each is
    # forwarded as a SAM --parameter-override only when non-empty.
    [string]$CloudflareTurnstileSecret = "",
    [string]$ElevenLabsApiKey          = "",
    [string]$ElevenLabsPhoneNumberId   = "",

    # Twilio SMS for the inbound demo line's "text me the starter pack" option.
    # Leave empty to keep that option hidden (offered only when all three are set).
    [string]$TwilioAccountSid          = "",
    [string]$TwilioAuthToken           = "",
    [string]$TwilioSmsFrom             = "",
    # Optional override of the link texted to callers (template default points
    # at the shadow-evaluation guide).
    [string]$StarterPackUrl            = ""
)

$ErrorActionPreference = "Stop"

# --- Prerequisite checks -----------------------------------------------------
# `make` was missing on this machine, so the SAM/AWS CLIs may be too. Fail early
# with actionable guidance instead of a cryptic command-not-found mid-deploy.
function Test-Cli([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$missing = @()
if (-not (Test-Cli "sam")) { $missing += "sam" }
if (-not (Test-Cli "aws")) { $missing += "aws" }

if ($missing.Count -gt 0) {
    Write-Host "Missing required CLI tool(s): $($missing -join ', ')" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install them (run in an elevated PowerShell if winget needs it):"
    if ($missing -contains "aws") { Write-Host "  winget install -e --id Amazon.AWSCLI" }
    if ($missing -contains "sam") { Write-Host "  winget install -e --id Amazon.SAM-CLI" }
    Write-Host ""
    Write-Host "Then configure credentials/region:"
    Write-Host "  aws configure"
    Write-Host ""
    Write-Host "Close and reopen PowerShell after installing so PATH refreshes, then re-run .\deploy.ps1."
    exit 1
}

# Assemble the shared AWS args once, here, so the credential check and the SAM
# calls below all use the same region/profile.
$awsArgs = @("--region", $Region)
if ($AwsProfile) { $awsArgs += @("--profile", $AwsProfile) }

# Confirm AWS credentials actually resolve before spending time on `sam build`.
Write-Host "Checking AWS credentials..." -ForegroundColor Cyan
$identity = aws sts get-caller-identity @awsArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "AWS credentials are not configured or are invalid:" -ForegroundColor Red
    Write-Host $identity
    Write-Host ""
    Write-Host "Run 'aws configure' (or set the right --AwsProfile) and try again."
    exit 1
}

# --- Assemble parameter overrides (only non-empty values) --------------------
$overrides = @()
if ($CloudflareTurnstileSecret) { $overrides += "CloudflareTurnstileSecret=$CloudflareTurnstileSecret" }
if ($ElevenLabsApiKey)          { $overrides += "ElevenLabsApiKey=$ElevenLabsApiKey" }
if ($ElevenLabsPhoneNumberId)   { $overrides += "ElevenLabsPhoneNumberId=$ElevenLabsPhoneNumberId" }
if ($TwilioAccountSid)          { $overrides += "TwilioAccountSid=$TwilioAccountSid" }
if ($TwilioAuthToken)           { $overrides += "TwilioAuthToken=$TwilioAuthToken" }
if ($TwilioSmsFrom)             { $overrides += "TwilioSmsFrom=$TwilioSmsFrom" }
if ($StarterPackUrl)            { $overrides += "StarterPackUrl=$StarterPackUrl" }

# Masked summary — never echo the secret values themselves.
$setNames = @()
if ($CloudflareTurnstileSecret) { $setNames += "CloudflareTurnstileSecret" }
if ($ElevenLabsApiKey)          { $setNames += "ElevenLabsApiKey" }
if ($ElevenLabsPhoneNumberId)   { $setNames += "ElevenLabsPhoneNumberId" }
if ($TwilioAccountSid)          { $setNames += "TwilioAccountSid" }
if ($TwilioAuthToken)           { $setNames += "TwilioAuthToken" }
if ($TwilioSmsFrom)             { $setNames += "TwilioSmsFrom" }
if ($StarterPackUrl)            { $setNames += "StarterPackUrl" }
Write-Host ""
Write-Host "Stack:   $StackName" -ForegroundColor Cyan
Write-Host "Region:  $Region"   -ForegroundColor Cyan
if ($setNames.Count -gt 0) {
    Write-Host "Secrets passed (values hidden): $($setNames -join ', ')" -ForegroundColor Cyan
} else {
    Write-Host "Secrets passed: none (baseline deploy; template defaults to empty)" -ForegroundColor Cyan
}
Write-Host ""

# --- Build -------------------------------------------------------------------
Write-Host "Running 'sam build'..." -ForegroundColor Cyan
sam build @awsArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "sam build failed (exit $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}

# --- Deploy ------------------------------------------------------------------
$deployArgs = @(
    "deploy",
    "--stack-name", $StackName,
    "--capabilities", "CAPABILITY_IAM",
    "--resolve-s3"
) + $awsArgs
if ($overrides.Count -gt 0) {
    $deployArgs += "--parameter-overrides"
    $deployArgs += $overrides
}

Write-Host "Running 'sam deploy'..." -ForegroundColor Cyan
sam @deployArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "sam deploy failed (exit $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}

# --- Report the base URL + the URLs it unblocks ------------------------------
$apiBaseUrl = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" `
    --output text @awsArgs
$apiBaseUrl = "$apiBaseUrl".Trim()

Write-Host ""
Write-Host "Deploy complete." -ForegroundColor Green
if ($apiBaseUrl -and $apiBaseUrl -ne "None") {
    Write-Host ""
    Write-Host "ApiBaseUrl: $apiBaseUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next-step webhook URLs (paste into the respective dashboards):"
    Write-Host "  Twilio 'A call comes in' (POST):     $apiBaseUrl/v1/webhooks/twilio-demo/voice"
    Write-Host "  ElevenLabs post-call webhook (POST): $apiBaseUrl/v1/webhooks/elevenlabs/postcall"
    Write-Host ""
    Write-Host "Quick sanity check (no auth):  curl $apiBaseUrl/health"
} else {
    Write-Host "Could not read the ApiBaseUrl output; check the stack in the CloudFormation console." -ForegroundColor Yellow
}
