<#
register_schtask.ps1

PowerShell helper to register a Windows Scheduled Task that runs the auto_fix_issues.py script hourly.

IMPORTANT:
- Set GITHUB_TOKEN as a system/user environment variable before registering the task (do NOT put tokens in files).
  Example (PowerShell, admin):
    setx GITHUB_TOKEN "<token>" /M
  Or set it for the current user without /M.
- Replace $PythonPath if your python executable is in a different location.
- Run this script in an elevated PowerShell session if you want to register a task that runs whether the user is logged on.
#>

param(
    [string]$PythonPath = "C:\\Python310\\python.exe",
    [string]$ScriptPath = "H:\\ProjectInsight\\auto_fix_issues.py",
    [string]$TaskName = "ProjectInsight-AutoFix"
)

Write-Host "Registering scheduled task '$TaskName' to run script: $ScriptPath"
Write-Host "Ensure GITHUB_TOKEN is set in the environment of the account that will run this task."

# Action: run Python with script path
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`""

# Trigger: start one minute from now, then repeat every 60 minutes indefinitely
$startTime = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger -Once -At $startTime -RepetitionInterval (New-TimeSpan -Minutes 60) -RepetitionDuration ([TimeSpan]::MaxValue)

# Register the task for the current user; change -User and -Password if you need a specific account
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "Hourly auto-fix issues task for ProjectInsight" -RunLevel Highest -Force
    Write-Host "Scheduled task '$TaskName' registered successfully."
    Write-Host "Note: verify the task's ""Settings"" in Task Scheduler (e.g., Run whether user is logged on) and that the account has the GITHUB_TOKEN environment variable set."
} catch {
    Write-Error "Failed to register scheduled task: $_"
}

Write-Host "Done. To remove the task: Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false"}