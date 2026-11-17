param([Parameter(Mandatory = $true)][string]$AgentPath)
$ErrorActionPreference = 'Stop'
$AgentPath = (Resolve-Path -LiteralPath $AgentPath).Path
$serviceName = 'monitor-agent-ci'

function Invoke-Agent([string[]]$AgentArgs) {
    & $AgentPath @AgentArgs
    if ($LASTEXITCODE -ne 0) { throw "Agent failed: $($AgentArgs[0])" }
}

try {
    Invoke-Agent -AgentArgs @('install', '--service-name', $serviceName, '--server', 'http://127.0.0.1:9', '--token', 'ci-token')
    (Get-Service -Name $serviceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(20))
    Invoke-Agent -AgentArgs @('status', '--service-name', $serviceName)
    Invoke-Agent -AgentArgs @('install', '--service-name', $serviceName)
    (Get-Service -Name $serviceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(20))
    Invoke-Agent -AgentArgs @('stop', '--service-name', $serviceName)
    (Get-Service -Name $serviceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(20))
    Invoke-Agent -AgentArgs @('start', '--service-name', $serviceName)
    (Get-Service -Name $serviceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(20))
} finally {
    if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
        Invoke-Agent -AgentArgs @('uninstall', '--service-name', $serviceName)
    }
}
Write-Host 'PASS: Windows service install, upgrade, stop, start, and uninstall'
