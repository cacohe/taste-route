param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl
)

$ErrorActionPreference = "Stop"
$root = $BaseUrl.TrimEnd("/")

$health = Invoke-RestMethod -Uri "$root/health" -Method Get
if ($health.status -ne "ok") {
    throw "Health check did not return status=ok."
}

$homepageResponse = Invoke-WebRequest -Uri "$root/" -Method Get
if ($homepageResponse.StatusCode -ne 200 -or $homepageResponse.Content -notmatch "TasteRoute") {
    throw "Frontend smoke check failed."
}

$docs = Invoke-WebRequest -Uri "$root/openapi.json" -Method Get
if ($docs.StatusCode -ne 200) {
    throw "OpenAPI smoke check failed."
}

Write-Host "TasteRoute smoke checks passed for $root"
