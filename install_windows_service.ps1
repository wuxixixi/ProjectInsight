$ErrorActionPreference = 'Stop'

param(
    [string]$ServiceName = 'ProjectInsight',
    [string]$DisplayName = 'ProjectInsight Service',
    [string]$ProjectRoot = 'C:\ProjectInsight',
    [string]$Host = '0.0.0.0',
    [int]$Port = 8000
)

$nssmCommand = Get-Command nssm -ErrorAction Stop
$nssm = $nssmCommand.Source

$python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$logsDir = Join-Path $ProjectRoot 'logs'
$stdoutLog = Join-Path $logsDir 'service-stdout.log'
$stderrLog = Join-Path $logsDir 'service-stderr.log'
$appArgs = "-m uvicorn backend.app:app --host $Host --port $Port"

if (!(Test-Path $python)) {
    throw "Python executable not found: $python"
}

if (!(Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

foreach ($taskName in @($ServiceName, "$ServiceName-Backend", "$ServiceName-Now")) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
}

Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like '*uvicorn backend.app:app*' } |
    ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
        } catch {
        }
    }

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    try {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    } catch {
    }
    & $nssm remove $ServiceName confirm | Out-Null
    Start-Sleep -Seconds 2
}

& $nssm install $ServiceName $python $appArgs | Out-Null
& $nssm set $ServiceName AppDirectory $ProjectRoot | Out-Null
& $nssm set $ServiceName DisplayName $DisplayName | Out-Null
& $nssm set $ServiceName Description 'ProjectInsight FastAPI service hosted by NSSM' | Out-Null
& $nssm set $ServiceName Start SERVICE_AUTO_START | Out-Null
& $nssm set $ServiceName ObjectName LocalSystem | Out-Null
& $nssm set $ServiceName AppStdout $stdoutLog | Out-Null
& $nssm set $ServiceName AppStderr $stderrLog | Out-Null
& $nssm set $ServiceName AppRotateFiles 1 | Out-Null
& $nssm set $ServiceName AppRotateOnline 1 | Out-Null
& $nssm set $ServiceName AppRotateBytes 10485760 | Out-Null
& $nssm set $ServiceName AppThrottle 1500 | Out-Null
& $nssm set $ServiceName AppExit Default Restart | Out-Null
& $nssm set $ServiceName AppStopMethodSkip 6 | Out-Null

Start-Service -Name $ServiceName
Start-Sleep -Seconds 5

$service = Get-Service -Name $ServiceName
$portListening = [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)

Write-Host "ServiceName: $($service.Name)"
Write-Host "DisplayName: $($service.DisplayName)"
Write-Host "Status: $($service.Status)"
Write-Host "StartType: Auto"
Write-Host "PortListening: $portListening"
