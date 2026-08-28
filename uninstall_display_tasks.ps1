[CmdletBinding()]
$ErrorActionPreference = 'Stop'
$TaskPath = '\acc_watcher\'
$names = @('SteamLinkDisplay-On', 'SteamLinkDisplay-Off')

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$p = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$PSCommandPath`")
    exit
}

foreach ($name in $names) {
    Unregister-ScheduledTask -TaskPath $TaskPath -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed $TaskPath$name"
}
