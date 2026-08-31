[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('on', 'off')]
    [string]$Mode
)

$ErrorActionPreference = 'Stop'
$LogDir = Join-Path $env:LOCALAPPDATA 'acc_watcher'
$LogFile = Join-Path $LogDir 'display_manager.log'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Write-Log([string]$Message) {
    Add-Content -LiteralPath $LogFile -Value ("{0} [INFO] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'), $Message)
}

function Get-Vdd {
    $names = @('Virtual Display Driver', 'IddSampleDriver Device HDR')
    $device = Get-PnpDevice -Class Display -ErrorAction Stop |
        Where-Object { $_.FriendlyName -in $names } |
        Select-Object -First 1
    if (-not $device) { throw 'Virtual Display Driver not found.' }
    return $device
}

try {
    Write-Log "Requested display mode: $Mode"
    $vdd = Get-Vdd

    if ($Mode -eq 'on') {
        if ($vdd.Status -ne 'OK') {
            Write-Log 'Enabling VDD'
            Enable-PnpDevice -InstanceId $vdd.InstanceId -Confirm:$false -ErrorAction Stop
            Start-Sleep -Seconds 2
        } else {
            Write-Log 'VDD already enabled'
        }

#        $displaySwitch = Join-Path $env:WINDIR 'System32\DisplaySwitch.exe'
#        Write-Log 'Selecting external display'
#        $p = Start-Process -FilePath $displaySwitch -ArgumentList '/external' -Wait -PassThru
#        if ($p.ExitCode -ne 0) { throw "DisplaySwitch /external failed with exit code $($p.ExitCode)." }
    }
    else {
 #       $displaySwitch = Join-Path $env:WINDIR 'System32\DisplaySwitch.exe'
 #       Write-Log 'Selecting internal display'
 #       $p = Start-Process -FilePath $displaySwitch -ArgumentList '/internal' -Wait -PassThru
 #       if ($p.ExitCode -ne 0) { throw "DisplaySwitch /internal failed with exit code $($p.ExitCode)." }
 #       Start-Sleep -Seconds 2

        $vdd = Get-Vdd
        if ($vdd.Status -eq 'OK') {
            Write-Log 'Disabling VDD'
            Disable-PnpDevice -InstanceId $vdd.InstanceId -Confirm:$false -ErrorAction Stop
        } else {
            Write-Log 'VDD already disabled'
        }
    }

    Write-Log "Display mode $Mode completed successfully"
    exit 0
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    exit 1
}
