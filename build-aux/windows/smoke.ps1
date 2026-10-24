# Starts the bundled Windows build (bundle.sh) the way a user would, with no MSYS2 on PATH, and photographs it.
#
#   smoke.ps1 -App <unzipped Dailies directory> -Screenshots <output directory>
#
# First `dailies --smoke`, which opens the window and quits once it has drawn: it must exit 0 and log no Python
# traceback or GLib CRITICAL. Then Dailies.cmd, the user's way in: its pythonw.exe must still run 15 s later. Then two
# runs, each photographed after 25 s (catalog refresh and first paint): the Popular section in an 800x560 window, so the
# window's own decorations and shadow show against the desktop, and the same under LANGUAGE=nl, for the translations.
# Either run exiting before its screenshot fails the script.
param(
    [Parameter(Mandatory)] [string] $App,
    [Parameter(Mandatory)] [string] $Screenshots
)

# Only Windows itself: the bundle finds its DLLs next to python.exe, as on a user's machine.
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
$python = Join-Path $App 'bin\python.exe'
$dailies = Join-Path $App 'bin\dailies'

$output = & $python $dailies --smoke 2>&1 | Out-String
Write-Output $output
if ($LASTEXITCODE -ne 0) { throw "dailies --smoke exited with $LASTEXITCODE" }
if ($output -match 'Traceback|CRITICAL') { throw 'dailies --smoke logged an error' }
# Set only after the native call, so that its stderr lines, captured above, can never end the script early.
$ErrorActionPreference = 'Stop'

Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\cmd.exe') -ArgumentList '/c', "`"$App\Dailies.cmd`""
Start-Sleep -Seconds 15
$started = @(Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$App\*" })
if ($started.Count -eq 0) { throw 'Dailies.cmd started no Dailies that was still running 15 s later' }
$started | Stop-Process
$started | ForEach-Object { $_.WaitForExit() }

# The State settings, in GLib's registry backend: the window size and the section the window opens on.
$state = 'HKCU:\Software\GSettings\io\github\tim_van_oudheusden\Dailies\State'
New-Item -Force $state | Out-Null
New-ItemProperty -Force $state -Name width -PropertyType DWord -Value 800 | Out-Null
New-ItemProperty -Force $state -Name height -PropertyType DWord -Value 560 | Out-Null
New-ItemProperty -Force $state -Name last-section -PropertyType String -Value 'popular' | Out-Null

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
New-Item -ItemType Directory -Force $Screenshots | Out-Null

function Capture([string] $name) {
    # python.exe for its stderr, without the console window it would open over the app's.
    $info = [System.Diagnostics.ProcessStartInfo]::new($python, "`"$dailies`"")
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::Start($info)
    $stderr = $process.StandardError.ReadToEndAsync()
    Start-Sleep -Seconds 25
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    [System.Drawing.Graphics]::FromImage($bitmap).CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $bitmap.Save((Join-Path $Screenshots "$name.png"))
    $alive = -not $process.HasExited
    if ($alive) { $process.Kill() }
    $process.WaitForExit()
    Write-Output $stderr.Result
    if (-not $alive) { throw "Dailies exited before the $name screenshot" }
}

Capture 'popular'
$env:LANGUAGE = 'nl'
Capture 'popular-nl'
