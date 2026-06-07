@{
    ModuleVersion = '1.3.0'
    GUID = 'a1b2c3d4-5e6f-7890-abcd-ef1234567890'
    Author = 'Brianna Baynard'
    CompanyName = 'NHID-Clinical'
    Copyright = '(c) 2026 Brianna Baynard. CC BY 4.0'
    Description = 'Official PowerShell module for NHID-Clinical v1.3 — screen AI voice calls, generate attestations, enforce disclosure rules. Built for payer IT teams.'
    PowerShellVersion = '5.1'
    FunctionsToExport = @('New-NHIDAttestation','Invoke-NHIDPayerScreen','Test-NHIDCompliance','Get-NHIDStateRequirements','Export-NHIDAuditFHIR')
    PrivateData = @{
        PSData = @{
            Tags = @('Healthcare','AI','Compliance','HIPAA','Payer','VoiceAI','NHID')
            ProjectUri = 'https://github.com/thankcheeses/NHID-Clinical'
            LicenseUri = 'https://creativecommons.org/licenses/by/4.0/'
        }
    }
}