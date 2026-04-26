<#
register_schtask.ps1

Registers an hourly Windows Scheduled Task for ProjectInsight auto-fix.
#>

param(
    [string]$RunnerPath = "H:\ProjectInsight\run_auto_fix.bat",
    [string]$TaskName = "ProjectInsight-AutoFix"
)

Write-Host "Registering scheduled task '$TaskName' to run: $RunnerPath"
Write-Host "Ensure GITHUB_TOKEN is set in the environment of the account that will run this task."

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$RunnerPath`""
$startTime = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger -Once -At $startTime -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Hourly auto-fix issues task for ProjectInsight" -RunLevel Highest -Force
    Write-Host "Scheduled task '$TaskName' registered successfully."
} catch {
    Write-Error "Failed to register scheduled task: $_"
}

Write-Host "Remove with: Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
