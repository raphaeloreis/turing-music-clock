# Roda o Turing Music Clock usando o Python do ambiente virtual (.venv)
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Ambiente virtual nao encontrado. Rode primeiro:  .\install.ps1" -ForegroundColor Yellow
    exit 1
}
& $py (Join-Path $root "music-visualizer.py")
