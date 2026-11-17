param(
    [string]$Server,
    [string]$Token,
    [string]$ServiceName = 'monitor-agent',
    [string]$Interface,
    [switch]$Insecure
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Open PowerShell as Administrator, then run this script again.'
}
$agent = Join-Path $PSScriptRoot 'monitor-agent.exe'
if (-not (Test-Path -LiteralPath $agent)) { throw 'Extract the release ZIP first; monitor-agent.exe must be next to Install.ps1.' }
$stream = [IO.File]::OpenRead($agent)
$reader = [IO.BinaryReader]::new($stream)
try {
    $stream.Position = 0x3c
    $peOffset = $reader.ReadUInt32()
    $stream.Position = $peOffset
    if ($reader.ReadUInt32() -ne 0x4550) { throw 'Invalid Windows executable.' }
    $machine = $reader.ReadUInt16()
} finally { $reader.Dispose(); $stream.Dispose() }
$osArch = $env:PROCESSOR_ARCHITEW6432
if (-not $osArch) { $osArch = $env:PROCESSOR_ARCHITECTURE }
if ($osArch -eq 'ARM64' -and $machine -ne 0xaa64) {
    throw 'Download monitor-agent-aarch64-pc-windows-msvc.zip for Windows ARM64.'
}
if ($osArch -eq 'AMD64' -and $machine -ne 0x8664) { throw 'Download the x86_64 Windows package.' }
$agentArgs = @('install', '--service-name', $ServiceName)
if ($Server) { $agentArgs += @('--server', $Server) }
if ($Token) { $agentArgs += @('--token', $Token) }
if ($PSBoundParameters.ContainsKey('Interface')) { $agentArgs += @('--iface', $Interface) }
if ($Insecure) { $agentArgs += '--insecure' }
& $agent @agentArgs
if ($LASTEXITCODE -ne 0) { throw 'Agent installation failed. Check the error above.' }
Write-Host 'Monitor Agent is installed. Check the node in your Hub panel.'
