param(
    [int]$Count = 50,
    [string]$ApiUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

function Convert-LevelToSeverity([string]$Level) {
    switch ($Level) {
        "Critical" { return "critical" }
        "Error" { return "high" }
        "Warning" { return "medium" }
        default { return "info" }
    }
}

$events = Get-WinEvent -LogName System -MaxEvents $Count | ForEach-Object {
    [ordered]@{
        source = "windows-system"
        event_type = "windows_event_$($_.Id)"
        severity = Convert-LevelToSeverity $_.LevelDisplayName
        message = $_.Message
        metadata = @{
            event_id = $_.Id
            provider = $_.ProviderName
            level = $_.LevelDisplayName
            time_created = $_.TimeCreated.ToUniversalTime().ToString("o")
        }
    }
}

$jsonPath = Join-Path $env:TEMP "bootcamp-windows-logs.json"
$events | ConvertTo-Json -Depth 6 | Set-Content -Path $jsonPath -Encoding UTF8

try {
    curl.exe -sS -f -X POST "$ApiUrl/ingest" -F "file=@$jsonPath;type=application/json"
    Write-Host "Logs Windows envoyes depuis le journal System."
}
finally {
    Remove-Item $jsonPath -Force -ErrorAction SilentlyContinue
}