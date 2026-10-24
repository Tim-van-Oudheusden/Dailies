# Runs the experimental installer (Dailies.iss) the way a user would, silently and for the current user only, then
# checks what it promises:
#
#   install-smoke.ps1 -Installer <Dailies-…-setup.exe> -Dir <install directory>
#
# The installer exits 0 and has started Dailies itself (the ticked box on its last page, which a silent install runs):
# a pythonw.exe from -Dir still runs 15 s later. The Start-menu shortcut exists, points at that pythonw.exe and starts
# Dailies again the same way. The uninstaller removes the shortcut and every file, including the bytecode Python wrote.
param(
    [Parameter(Mandatory)] [string] $Installer,
    [Parameter(Mandatory)] [string] $Dir
)
$ErrorActionPreference = 'Stop'

function Get-Installed {
    @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$Dir\*" })
}

function Stop-Dailies([string] $after) {
    Start-Sleep -Seconds 15
    $running = @(Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$Dir\*" })
    if ($running.Count -eq 0) { throw "$after started no Dailies that was still running 15 s later" }
    $running | Stop-Process
    $running | ForEach-Object { $_.WaitForExit() }
    # GLib's session bus (gdbus.exe, started by GApplication) quits 3 s after its last client; until then it holds
    # files in bin\ open, which neither the next start nor the uninstaller should meet.
    for ($second = 0; (Get-Installed).Count -gt 0 -and $second -lt 30; $second++) { Start-Sleep -Seconds 1 }
    Get-Installed | ForEach-Object { throw "$($_.Path) still ran 30 s after Dailies quit" }
}

# Start-Process -Wait would also wait for the Dailies the installer starts, so wait for the installer process only.
function Invoke-Silently([string] $program, [string[]] $arguments) {
    $process = Start-Process -PassThru -FilePath $program -ArgumentList $arguments
    $null = $process.Handle  # keeps the handle open, or ExitCode stays empty once the process has gone
    if (-not $process.WaitForExit(300000)) { throw "$program still ran after 5 minutes" }
    $process.ExitCode
}

$log = Join-Path ([IO.Path]::GetTempPath()) 'dailies-install.log'
$status = Invoke-Silently $Installer @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=`"$Dir`"", "/LOG=`"$log`"")
if ($status -ne 0) {
    Get-Content $log
    throw "the installer exited with $status"
}
Stop-Dailies 'The installer'

$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Dailies.lnk'
if (-not (Test-Path $shortcut)) { throw "no Start-menu shortcut at $shortcut" }
$link = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
Write-Output "Start menu: $($link.TargetPath) $($link.Arguments)"
if ($link.TargetPath -ne (Join-Path $Dir 'bin\pythonw.exe')) { throw "the shortcut starts $($link.TargetPath)" }
Start-Process -FilePath $shortcut
Stop-Dailies 'The Start-menu shortcut'

# The uninstaller hands over to a copy of itself in %TEMP% and returns at once; it deletes itself last.
$uninstaller = Join-Path $Dir 'unins000.exe'
$status = Invoke-Silently $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
if ($status -ne 0) { throw "the uninstaller exited with $status" }
for ($second = 0; (Test-Path $uninstaller) -and $second -lt 120; $second++) { Start-Sleep -Seconds 1 }
if (Test-Path $uninstaller) { throw 'the uninstaller had not finished after 2 minutes' }
if (Test-Path $shortcut) { throw 'the uninstaller left the Start-menu shortcut' }
$left = @(if (Test-Path $Dir) { Get-ChildItem -Recurse -File $Dir })
if ($left.Count -gt 0) {
    $left | Select-Object -First 50 | ForEach-Object { "left behind: $($_.FullName)" }
    throw "the uninstaller left $($left.Count) files in $Dir"
}
