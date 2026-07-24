# =============================================================================
#  Configura o Turing Music Clock para iniciar junto com o Windows.
#  Cria uma tarefa agendada (ao logon, +30s, oculta) que roda sem janela.
#  Nao precisa de administrador.
# =============================================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot            # pasta do projeto (scripts/ esta dentro dela)
$pyw  = Join-Path $root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pyw)) { throw "Ambiente virtual nao encontrado. Rode .\install.ps1 primeiro." }

$me = "$env:USERDOMAIN\$env:USERNAME"
$action  = New-ScheduledTaskAction -Execute $pyw -Argument "music-visualizer.py" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $me
$trigger.Delay = "PT30S"
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -Hidden
$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description "Turing Music Clock"

Register-ScheduledTask -TaskName "TuringMusicClock" -InputObject $task -Force | Out-Null
Write-Host "OK! Tarefa 'TuringMusicClock' criada (inicia ao logon, +30s, oculta)." -ForegroundColor Green
Write-Host "Para remover:  Unregister-ScheduledTask -TaskName TuringMusicClock"
