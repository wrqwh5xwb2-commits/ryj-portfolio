param([string]$PythonPath = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    if (-not $PythonPath) {
        $managedPython = Join-Path $env:USERPROFILE '.workbuddy\binaries\python\versions\3.13.12\python.exe'
        if (Test-Path -LiteralPath $managedPython) { $PythonPath = $managedPython }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { $PythonPath = (Get-Command python).Source }
        else { throw 'Install Python 3.13 or run setup.cmd -PythonPath "C:\path\python.exe".' }
    }
    $pythonVersion = & $PythonPath -c 'import sys; print("%d.%d" % sys.version_info[:2])'
    if ($pythonVersion -ne '3.13') { throw 'Use Python 3.13: setup.cmd -PythonPath "C:\path\python.exe".' }
    & $PythonPath -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python environment.' }
}
& $venvPython -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
Write-Host 'Ready. Run start.cmd to generate and open reports.'
