# Run this script as Administrator.
# Enables virtualization features needed by WSL2/Buildozer and configures hypervisor launch.

$ErrorActionPreference = 'Stop'

Write-Host "Enabling VirtualMachinePlatform..."
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart

Write-Host "Enabling HypervisorPlatform..."
Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All -NoRestart

Write-Host "Setting hypervisor launch to auto..."
bcdedit /set hypervisorlaunchtype auto

Write-Host "Installing WSL (if not already installed)..."
wsl --install --no-distribution

Write-Host "Done. Reboot required. After reboot, install Ubuntu and run buildozer in WSL."
