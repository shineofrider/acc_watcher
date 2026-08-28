[CmdletBinding()]
param(
    [string]$ExecutablePath = ""
)

$ErrorActionPreference = 'Stop'
$TaskOn = 'acc_watcher\SteamLinkDisplay-On'
$TaskOff = 'acc_watcher\SteamLinkDisplay-Off'

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    $args = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"")
    if ($ExecutablePath) { $args += @('-ExecutablePath', "`"$ExecutablePath`") }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $args
    exit
}

if (-not $ExecutablePath) {
    $candidate = Join-Path $PSScriptRoot 'dist\acc_watcher.exe'
    if (Test-Path $candidate) {
        $ExecutablePath = $candidate
    } else {
        throw 'acc_watcher.exe not found. Build the project first or use -ExecutablePath.'
    }
}

$ExecutablePath = (Resolve-Path $ExecutablePath).Path
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType InteractiveToken `
    -RunLevel Highest

function Register-DisplayTask {
    param([string]$Name, [string]$Mode)
    $action = New-ScheduledTaskAction -Execute $ExecutablePath -Argument "--display-mode $Mode"
    Register-ScheduledTask -TaskName $Name -Action $action -Principal $principal -Force | Out-Null
    Write-Host "Installed $Name"
}

Register-DisplayTask -Name $TaskOn -Mode 'on'
Register-DisplayTask -Name $TaskOff -Mode 'off'
Write-Host ''
Write-Host 'Display tasks installed successfully.' -ForegroundColor Green
Write-Host "Executable: $ExecutablePath"
