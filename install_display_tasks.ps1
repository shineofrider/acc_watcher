[CmdletBinding()]
param(
    [string]$ExecutablePath = ""
)

$ErrorActionPreference = 'Stop'
$TaskPath = '\acc_watcher\'
$TaskOn = 'SteamLinkDisplay-On'
$TaskOff = 'SteamLinkDisplay-Off'
$ScriptPath = Join-Path $PSScriptRoot 'display_manager.ps1'

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($ExecutablePath) { $argList += " -ExecutablePath `"$ExecutablePath`"" }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
    exit
}

if (-not (Test-Path -LiteralPath $ScriptPath)) {
    throw "display_manager.ps1 not found: $ScriptPath"
}

$ScriptPath = (Resolve-Path $ScriptPath).Path
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Highest

$service = New-Object -ComObject 'Schedule.Service'
$service.Connect()
$root = $service.GetFolder('\')
$folderPath = $TaskPath.TrimEnd('\')
try {
    $null = $root.GetFolder($folderPath)
} catch {
    try { $null = $root.CreateFolder($folderPath, $null) }
    catch {
        if ($_.Exception.HResult -ne -2147024713) { throw }
    }
}

function Register-DisplayTask {
    param([string]$Name, [string]$Mode)
    $action = New-ScheduledTaskAction `
        -Execute 'powershell.exe' `
        -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`" -Mode $Mode"
    Register-ScheduledTask -TaskPath $TaskPath -TaskName $Name -Action $action -Principal $principal -Force | Out-Null
    Write-Host "Installed $TaskPath$Name"
}

Register-DisplayTask -Name $TaskOn -Mode 'on'
Register-DisplayTask -Name $TaskOff -Mode 'off'
Write-Host ''
Write-Host 'Display tasks installed successfully.' -ForegroundColor Green
Write-Host "Display manager: $ScriptPath"
