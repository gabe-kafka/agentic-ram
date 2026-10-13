# sync-concept-into-rss.ps1 -Rss <model.rss> -Cpt <calculated.cpt> [-ExpectMember <sha12>] [-Member cpt1027E]
#                           [-WaitMinutes N] [-ArchiveDir <dir>] [-DryRun]
# Put a saved RAM Concept file into a RAM Structural System model: build the new .rss locally, archive the current
# one (timestamped), replace it, prove the member hash. The source .rss is never edited in place.
#   -ExpectMember  refuse unless the Concept member now in the .rss has this sha256 prefix (nobody saved since the
#                  state the change was built on). Get it with rss_member.py --hash.
#   -Member        the member suffix when the archive holds more than one Concept file (2636: cpt1027E elevated, cpt1027M mat).
#   -WaitMinutes   RAM Manager writes <model>.usr beside a model it has open; wait up to this long for it to go away.
#   -ArchiveDir    where the replaced file goes; default <rss folder>\Archive (created if missing).
#   -DryRun        build and verify the new .rss in the work folder only; the model on disk is not touched.
# Work folder: <repo>\ram-structural-system\models\sync-<model>-<stamp>\ (ignored by git).
param([Parameter(Mandatory = $true)][string]$Rss, [Parameter(Mandatory = $true)][string]$Cpt, [string]$ExpectMember = '',
      [string]$Member = '', [int]$WaitMinutes = 0, [string]$ArchiveDir = '', [switch]$DryRun)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = (Resolve-Path (Join-Path $here '..\..\..\..')).Path
$swap = Join-Path $repo 'ram-structural-system\scripts\swap-concept-into-rss.py'
$memberTool = Join-Path $here 'rss_member.py'
if (-not (Test-Path -LiteralPath $Rss)) { throw "no such model: $Rss" }
if (-not (Test-Path -LiteralPath $Cpt)) { throw "no such Concept file: $Cpt" }
if ((Test-Path -LiteralPath "$Cpt-journal") -or (Test-Path -LiteralPath "$Cpt-wal")) { throw "$Cpt has a journal beside it; it is still open somewhere" }
$name = [System.IO.Path]::GetFileNameWithoutExtension($Rss)
$dir = Split-Path -Parent $Rss
$lock = Join-Path $dir "$name.usr"
$deadline = (Get-Date).AddMinutes($WaitMinutes)
while ((Test-Path -LiteralPath $lock) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 3 }
if (Test-Path -LiteralPath $lock) { throw "RAM Manager has $name open (.usr lock beside it); close it first" }
if ($WaitMinutes) { Start-Sleep -Seconds 6 }
$memberArgs = @(); if ($Member) { $memberArgs = @('--member', $Member) }
$now = (python $memberTool $Rss --hash @memberArgs | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw $now }
$memberName, $nowHash = $now -split ' '
"member $memberName now $($nowHash.Substring(0, 12))"
if ($ExpectMember -and -not $nowHash.StartsWith($ExpectMember.ToLower())) { throw "the .rss holds $($nowHash.Substring(0, 12)), expected $ExpectMember`: it was saved since; not replaced" }
$cptHash = (Get-FileHash -LiteralPath $Cpt -Algorithm SHA256).Hash.ToLower()
if ($cptHash -eq $nowHash) { "the .rss already holds this Concept file ($($cptHash.Substring(0, 12))); nothing to do"; exit 0 }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$work = Join-Path $repo "ram-structural-system\models\sync-$name-$stamp"
New-Item -ItemType Directory -Force $work | Out-Null
$new = Join-Path $work "$name.rss"
$suffix = if ($Member) { $Member } else { ($memberName -split '\.')[-1] }
python $swap $Rss $Cpt $new $suffix
if ($LASTEXITCODE -ne 0) { throw 'swap failed' }
$built = ((python $memberTool $new --hash --member $suffix | Out-String).Trim() -split ' ')[1]
if ($built -ne $cptHash) { throw 'the built .rss does not hold the Concept file' }
if ($DryRun) { "DRY RUN: built and verified $new; $Rss not touched"; exit 0 }
if (-not $ArchiveDir) { $ArchiveDir = Join-Path $dir 'Archive' }
New-Item -ItemType Directory -Force $ArchiveDir | Out-Null
$archive = Join-Path $ArchiveDir ($name + '_' + $stamp + '.rss')
if (Test-Path -LiteralPath $archive) { throw "$archive exists" }
if (Test-Path -LiteralPath $lock) { throw 'RAM Manager opened the model again; not replaced' }
Copy-Item -LiteralPath $Rss $archive
if ((Get-FileHash -LiteralPath $Rss).Hash -ne (Get-FileHash -LiteralPath $archive).Hash) { throw 'archive copy does not match' }
Copy-Item -LiteralPath $new $Rss -Force
$after = ((python $memberTool $Rss --hash --member $suffix | Out-String).Trim() -split ' ')[1]
if ($after -ne $cptHash) { throw 'the model does not hold the Concept file after the replace' }
"archived to $archive"
"synced $name $(Get-Date -Format 'yyyy-MM-dd HH:mm'): member $suffix = $($cptHash.Substring(0, 12))"
