$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$matches = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains($projectPython) -and $_.CommandLine.Contains('launch.py')
}
if ($matches) {
    $matches | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
    Write-Output 'SupportLab stopped. Your data is preserved.'
} else {
    Write-Output 'SupportLab is not running.'
}
