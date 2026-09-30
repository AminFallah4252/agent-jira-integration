<#
.SYNOPSIS
    Cross-platform PowerShell wrapper for Jira Management CLI.
.DESCRIPTION
    Runs scripts/jira_cli.py using available python or python3 interpreter.
.EXAMPLE
    .\run.ps1 auth status
    .\run.ps1 board view --board-id 12
    .\run.ps1 issue transition --key PROJ-101 --to "In Review"
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliPath = Join-Path $scriptDir "jira_cli.py"

# Find python executable
$pythonExe = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $pythonExe = "python3"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonExe = "py"
} else {
    Write-Error "Python 3 is required to run Jira Management CLI. Please install Python."
    exit 1
}

& $pythonExe $cliPath @ScriptArgs
exit $LASTEXITCODE
