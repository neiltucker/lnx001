# ============================================================================== 
# Courseware Studio Single-Script Setup: LNX-001
# ============================================================================== 
#Requires -RunAsAdministrator

[CmdletBinding()]
param(
  [string]$DeployRoot = 'C:\LNX-001Deploy',
  [string]$VMName = 'LNX-001',
  [string]$SwitchName = 'Default Switch',
  [switch]$SkipVmCreation,
  [switch]$SkipGuestAutomation,
  [switch]$FailOnMissing
)

$ErrorActionPreference = 'Stop'

$CourseNumber = 'LNX-001'
$CourseTitle = 'Linux Administration Essentials'
$EnvironmentType = 'docker'
$OsTarget = 'windows'
$IsHyperV = $false
$IsDocker = $true
$LooksWindows = $true
$LooksLinux = $false
$AdministratorPassword = 'Pa$$w0rdPa$$w0rd'
$StudentPassword = 'Pa$$w0rd'
$HyperVRoot = Join-Path $DeployRoot 'HyperV'
$LogRoot = Join-Path $DeployRoot 'Logs'
$VmRoot = Join-Path $HyperVRoot 'VirtualMachines'
$VhdRoot = Join-Path $HyperVRoot 'VirtualHardDisks'
$VhdPath = Join-Path $VhdRoot ($VMName + '.vhdx')
$PayloadVhdPath = Join-Path $VhdRoot ('SetupPayload_' + $VMName + '.vhdx')

$FolderPlan = @(
  [pscustomobject]@{ Path = (Join-Path $DeployRoot 'Docker'); Purpose = 'Docker installer/package or project resources' },
  [pscustomobject]@{ Path = (Join-Path $DeployRoot 'CourseFiles'); Purpose = 'Course class files and lab resources' },
  [pscustomobject]@{ Path = (Join-Path $DeployRoot 'Logs'); Purpose = 'Setup and validation logs' }
)

$ResourcePlan = @(
  [pscustomobject]@{ Name = 'Course class files zip'; Folder = (Join-Path $DeployRoot 'CourseFiles'); ExpectedFiles = @('LNX-001_Classfiles.zip', '*.zip'); Required = $false; Kind = 'file'; Notes = 'Optional class files archive when the course includes downloadable lab resources.' }
)

function Write-Section {
  param([string]$Text)
  Write-Host ''
  Write-Host ('=' * 70) -ForegroundColor DarkGray
  Write-Host $Text -ForegroundColor Cyan
  Write-Host ('=' * 70) -ForegroundColor DarkGray
}

function Ensure-Folder {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return }
  if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null }
}

function Find-ExpectedResource {
  param($Resource)
  if (-not (Test-Path -LiteralPath $Resource.Folder)) { return $null }
  foreach ($pattern in @($Resource.ExpectedFiles)) {
    $exact = Join-Path $Resource.Folder $pattern
    if ($pattern -notmatch '[\*\?]' -and (Test-Path -LiteralPath $exact)) { return (Get-Item -LiteralPath $exact) }
    $candidate = Get-ChildItem -LiteralPath $Resource.Folder -Filter $pattern -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) { return $candidate }
  }
  return $null
}

function Test-SetupResources {
  $results = foreach ($resource in $ResourcePlan) {
    $candidate = Find-ExpectedResource -Resource $resource
    $exists = $null -ne $candidate
    [pscustomobject]@{
      Status = if ($resource.Required -and $exists) { 'FOUND' } elseif ($resource.Required) { 'MISSING' } elseif ($exists) { 'OPTIONAL FOUND' } else { 'OPTIONAL MISSING' }
      Name = $resource.Name
      Required = [bool]$resource.Required
      Exists = [bool]$exists
      Folder = $resource.Folder
      FoundPath = if ($candidate) { $candidate.FullName } else { $null }
      ExpectedFiles = ($resource.ExpectedFiles -join ', ')
      Notes = $resource.Notes
    }
  }

  Ensure-Folder -Path $LogRoot
  $jsonPath = Join-Path $LogRoot 'setup-resource-validation.json'
  $mdPath = Join-Path $LogRoot 'setup-resource-validation.md'
  $results | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

  $md = New-Object System.Collections.Generic.List[string]
  $md.Add('# Setup Resource Validation')
  $md.Add('')
  $md.Add("- Generated: $(Get-Date -Format s)")
  $md.Add("- Course: $CourseNumber")
  $md.Add("- Deployment root: $DeployRoot")
  $md.Add('')
  $md.Add('| Status | Resource | Required | Folder | Found path | Expected files | Notes |')
  $md.Add('|---|---|---:|---|---|---|---|')
  foreach ($item in $results) {
    $md.Add('| ' + $item.Status + ' | ' + $item.Name + ' | ' + $item.Required + ' | ' + $item.Folder + ' | ' + $item.FoundPath + ' | ' + $item.ExpectedFiles + ' | ' + $item.Notes + ' |')
  }
  $md | Set-Content -LiteralPath $mdPath -Encoding UTF8

  Write-Host ''
  Write-Host 'Setup resource checklist' -ForegroundColor Cyan
  foreach ($item in $results) {
    $color = if ($item.Status -eq 'FOUND' -or $item.Status -eq 'OPTIONAL FOUND') { 'Green' } elseif ($item.Status -eq 'MISSING') { 'Red' } else { 'DarkYellow' }
    Write-Host "[$($item.Status)] $($item.Name)" -ForegroundColor $color
    Write-Host "  Folder:   $($item.Folder)"
    Write-Host "  Expected: $($item.ExpectedFiles)"
    if ($item.FoundPath) { Write-Host "  Found:    $($item.FoundPath)" }
    if (-not $item.Exists -and $item.Required) { Write-Host "  Action:   Place the required resource in this folder." -ForegroundColor Yellow }
    Write-Host ''
  }
  Write-Host "Reports written:" -ForegroundColor Cyan
  Write-Host "  JSON:     $jsonPath"
  Write-Host "  Markdown: $mdPath"

  return @($results | Where-Object { $_.Required -and -not $_.Exists })
}

function Test-HyperVReady {
  if (-not $IsHyperV) { return }
  if (-not (Get-Command Get-VM -ErrorAction SilentlyContinue)) { throw 'Hyper-V PowerShell commands are not available. Install/enable Hyper-V and management tools.' }
  $vmms = Get-Service -Name vmms -ErrorAction SilentlyContinue
  if (-not $vmms -or $vmms.Status -ne 'Running') { throw 'Hyper-V Virtual Machine Management service is not running.' }
  Get-VMHost -ErrorAction Stop | Out-Null
}

function New-SetupPayloadVhd {
  if (-not $IsHyperV) { return }
  if (Test-Path -LiteralPath $PayloadVhdPath) {
    Write-Host 'Setup payload VHDX already exists. Skipping payload creation.' -ForegroundColor Yellow
    return
  }
  Write-Host 'Creating setup payload VHDX...' -ForegroundColor Cyan
  $payloadSizeBytes = [int64]50 * 1GB
  New-VHD -Path $PayloadVhdPath -Dynamic -SizeBytes $payloadSizeBytes | Out-Null
  $mounted = Mount-VHD -Path $PayloadVhdPath -PassThru
  try {
    $disk = $mounted | Get-Disk
    if ($disk.PartitionStyle -eq 'RAW') { Initialize-Disk -Number $disk.Number -PartitionStyle GPT | Out-Null }
    $partition = New-Partition -DiskNumber $disk.Number -UseMaximumSize -AssignDriveLetter
    Format-Volume -Partition $partition -FileSystem NTFS -NewFileSystemLabel 'SetupPayload' -Confirm:$false -Force | Out-Null
    $payloadDrive = "$($partition.DriveLetter):\"
    foreach ($folder in $FolderPlan) {
      if ($folder.Path -like "$DeployRoot\HyperV*") { continue }
      if ($folder.Path -like "$DeployRoot\Logs*") { continue }
      if (Test-Path -LiteralPath $folder.Path) {
        $dest = Join-Path $payloadDrive ((Split-Path -Path $folder.Path -Leaf))
        Copy-Item -Path $folder.Path -Destination $dest -Recurse -Force -ErrorAction SilentlyContinue
      }
    }
  }
  finally {
    Dismount-VHD -Path $PayloadVhdPath -ErrorAction SilentlyContinue
  }
}

function New-CourseHyperVVm {
  if (-not $IsHyperV -or $SkipVmCreation) { return }
  $existing = Get-VM -Name $VMName -ErrorAction SilentlyContinue
  if ($existing) {
    Write-Host "VM already exists: $VMName. Skipping VM creation." -ForegroundColor Yellow
    return
  }
  $osIsoPath = $null
  if (-not $osIsoPath) { throw 'Guest OS ISO was not found. Run resource validation and place the OS ISO before VM creation.' }
  Ensure-Folder -Path $VmRoot
  Ensure-Folder -Path $VhdRoot
  if (Test-Path -LiteralPath $VhdPath) { Remove-Item -LiteralPath $VhdPath -Force }
  Write-Host "Creating Hyper-V VM: $VMName" -ForegroundColor Cyan
  New-VM -Name $VMName -Path $VmRoot -Generation 2 -MemoryStartupBytes 8GB -SwitchName $SwitchName | Out-Null
  Set-VM -Name $VMName -ProcessorCount 4 -DynamicMemory -MemoryMinimumBytes 4GB -MemoryMaximumBytes 12GB | Out-Null
  New-VHD -Path $VhdPath -Dynamic -SizeBytes 120GB | Out-Null
  Add-VMHardDiskDrive -VMName $VMName -Path $VhdPath | Out-Null
  Add-VMDvdDrive -VMName $VMName -Path $osIsoPath | Out-Null
  if (Test-Path -LiteralPath $PayloadVhdPath) { Add-VMHardDiskDrive -VMName $VMName -Path $PayloadVhdPath | Out-Null }
  $dvdDrive = Get-VMDvdDrive -VMName $VMName
  $hardDisk = Get-VMHardDiskDrive -VMName $VMName | Select-Object -First 1
  Set-VMFirmware -VMName $VMName -BootOrder $dvdDrive, $hardDisk | Out-Null
  Enable-VMIntegrationService -VMName $VMName -Name "Guest Service Interface" -ErrorAction SilentlyContinue | Out-Null
  Start-VM -Name $VMName | Out-Null
}

function Invoke-WindowsGuestAutomation {
  if (-not $IsHyperV -or -not $LooksWindows -or $SkipGuestAutomation) { return }
  Write-Host ''
  Write-Host 'ACTION REQUIRED: install the guest OS if it is not already installed.' -ForegroundColor Yellow
  Write-Host 'When Windows is at the desktop, sign in as Administrator.'
  Write-Host 'Administrator password: Pa$$w0rdPa$$w0rd'
  Read-Host 'Press ENTER after the VM is at the Windows desktop' | Out-Null
  $guestCred = New-Object System.Management.Automation.PSCredential ('Administrator', (ConvertTo-SecureString $AdministratorPassword -AsPlainText -Force))
  Invoke-Command -VMName $VMName -Credential $guestCred -ScriptBlock {
    $ErrorActionPreference = 'Stop'
    $adminPassword = 'Pa$$w0rdPa$$w0rd'
    $studentPassword = 'Pa$$w0rd'
    Write-Host 'Configuring standard classroom accounts...'
    $accounts = @{ 'Administrator' = $adminPassword; 'Adminz' = $adminPassword; 'Student' = $studentPassword }
    foreach ($user in $accounts.Keys) {
      $secure = ConvertTo-SecureString $accounts[$user] -AsPlainText -Force
      if (Get-LocalUser -Name $user -ErrorAction SilentlyContinue) {
        Set-LocalUser -Name $user -Password $secure -PasswordNeverExpires $true
      } else {
        New-LocalUser -Name $user -Password $secure -FullName ($user + ' Account') -PasswordNeverExpires | Out-Null
      }
      Add-LocalGroupMember -Group 'Administrators' -Member $user -ErrorAction SilentlyContinue
    }
    Get-Disk | Where-Object IsOffline -eq $true | Set-Disk -IsOffline $false -ErrorAction SilentlyContinue
    $payloadVol = Get-Volume | Where-Object FileSystemLabel -eq 'SetupPayload' | Select-Object -First 1
    if ($payloadVol -and -not $payloadVol.DriveLetter) { Get-Partition -Volume $payloadVol | Set-Partition -AssignDriveLetter | Out-Null; $payloadVol = Get-Volume | Where-Object FileSystemLabel -eq 'SetupPayload' | Select-Object -First 1 }
    $payloadDrive = if ($payloadVol -and $payloadVol.DriveLetter) { "$($payloadVol.DriveLetter):\" } else { $null }
    if (-not (Test-Path 'C:\Classfiles')) { New-Item -ItemType Directory -Path 'C:\Classfiles' -Force | Out-Null }
    if (-not (Test-Path 'C:\Temp')) { New-Item -ItemType Directory -Path 'C:\Temp' -Force | Out-Null }
  }
}

Write-Section "Phase 1: Create deployment folders"
Ensure-Folder -Path $DeployRoot
Ensure-Folder -Path $LogRoot
foreach ($folder in $FolderPlan) { Ensure-Folder -Path $folder.Path; Write-Host "OK  $($folder.Path)" }

Write-Section "Phase 2: Validate setup resources"
$missing = @(Test-SetupResources)
if ($missing.Count -gt 0) {
  Write-Warning "Missing $($missing.Count) required setup resource(s). Place the missing files and run this script again."
  $global:LASTEXITCODE = 1
  if ($FailOnMissing) { throw "Missing required setup resources." }
  return
}

if ($IsDocker) {
  Write-Section "Docker target validation"
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker was not found. Install Docker before continuing." }
  docker version | Out-Host
}

if ($IsHyperV) {
  Write-Section "Phase 3: Validate Hyper-V"
  Test-HyperVReady
  Write-Section "Phase 4: Create setup payload"
  New-SetupPayloadVhd
  Write-Section "Phase 5: Create or validate VM"
  New-CourseHyperVVm
  Write-Section "Phase 6: Guest automation"
  Invoke-WindowsGuestAutomation
}

Write-Section "Setup complete"
Write-Host "Course setup workflow completed for $CourseNumber." -ForegroundColor Green
Write-Host "Review logs in $LogRoot."
$global:LASTEXITCODE = 0
