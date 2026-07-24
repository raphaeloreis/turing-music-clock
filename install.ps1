# =============================================================================
#  Turing Music Clock - instalador
#  Instala o Python (se faltar), cria o ambiente virtual e instala as deps.
#  Uso:  botao direito > "Executar com o PowerShell"  ou   .\install.ps1
# =============================================================================
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Write-Host "== Turing Music Clock - instalacao ==" -ForegroundColor Cyan

# --- 1) Python -------------------------------------------------------------
$pyExe = $null; $pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue)          { $pyExe = "py";     $pyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue)  { $pyExe = "python"; $pyArgs = @() }

if (-not $pyExe) {
    Write-Host "Python nao encontrado. Instalando via winget (Python 3.12)..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    # atualiza o PATH da sessao atual
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
    if (Get-Command py -ErrorAction SilentlyContinue)         { $pyExe = "py";     $pyArgs = @("-3") }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = "python"; $pyArgs = @() }
    if (-not $pyExe) { throw "Python foi instalado mas nao esta no PATH. Feche e reabra o PowerShell e rode .\install.ps1 de novo." }
}
Write-Host ("Python: " + (& $pyExe @pyArgs --version)) -ForegroundColor Green

# --- 2) Ambiente virtual ---------------------------------------------------
$venv = Join-Path $root ".venv"
$vpy  = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $vpy)) {
    Write-Host "Criando ambiente virtual (.venv)..."
    & $pyExe @pyArgs -m venv $venv
}

# --- 3) Dependencias -------------------------------------------------------
Write-Host "Instalando dependencias (pode demorar um pouco)..."
& $vpy -m pip install --upgrade pip --quiet
& $vpy -m pip install -r (Join-Path $root "requirements.txt")

Write-Host ""
Write-Host "Instalacao concluida!" -ForegroundColor Green
Write-Host "-------------------------------------------------------------"
Write-Host "Rodar agora:              .\run.ps1"
Write-Host "Iniciar com o Windows:    .\scripts\setup-autostart.ps1"
Write-Host "Temperatura da CPU:       requer o LibreHardwareMonitor (veja o README)"
Write-Host "-------------------------------------------------------------"

# --- 4) Autostart (opcional) ----------------------------------------------
$ans = Read-Host "Configurar para iniciar automaticamente com o Windows? (S/N)"
if ($ans -match '^[SsYy]') {
    & (Join-Path $root "scripts\setup-autostart.ps1")
}
