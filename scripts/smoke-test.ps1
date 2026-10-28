param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$ExpectedCommit = "",

    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$arguments = @(
    "$PSScriptRoot/smoke_test.py",
    "--base-url", $BaseUrl,
    "--timeout-seconds", $TimeoutSeconds
)
if ($ExpectedCommit) {
    $arguments += @("--expected-commit", $ExpectedCommit)
}

& python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "TasteRoute smoke checks failed with exit code $LASTEXITCODE."
}
