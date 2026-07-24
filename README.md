# Turing Music Clock

Visualizador de música + relógio digital com métricas de CPU/GPU para o display USB **Turing Smart Screen 3.5"**.

Quando há música tocando, mostra a capa, título e artista. Quando está ocioso, vira um **relógio** (dois estilos: digital 7-segmentos ou flip/painel de aeroporto) com **temperatura e uso de CPU e GPU** e a data.

> Fork de [turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) (via [spel987/turing-3.5-screen-music-visualizer](https://github.com/spel987/turing-3.5-screen-music-visualizer)). Veja os [créditos](#créditos).

<div align="center">

| Tocando | Relógio flip | Relógio digital |
|:---:|:---:|:---:|
| ![tocando](docs/now-playing.png) | ![flip](docs/idle-flip.png) | ![digital](docs/idle-digital.png) |

</div>

## ✨ Recursos

- 🎵 Tela "tocando" com capa, título, artista e fundo desfocado (lê a mídia do Windows via SMTC).
- 🕐 Tela ociosa com **relógio** em dois estilos (`digital` ou `flip`) — configurável.
- 🌡️ **Temperatura + uso de CPU e GPU** (temperatura da CPU colorida por faixa no modo digital).
- 📅 Data com dia da semana.
- 🪶 Leve (~0,5% de CPU, ~190 MB de RAM) — só redesenha a tela quando algo muda.
- 🚀 Instalador de 1 comando + autostart opcional com o Windows.

## 🖥️ Requisitos

| Item | Necessário para |
|---|---|
| **Turing Smart Screen 3.5"** (revisão A) | tudo — é o display alvo |
| **Windows** | a leitura da mídia (SMTC/`winrt`) é exclusiva do Windows |
| **Python 3.9–3.12** | o instalador instala via `winget` se faltar |
| **GPU NVIDIA** (opcional) | temperatura/uso da GPU (via `nvidia-smi`, já vem no driver) |
| **LibreHardwareMonitor** (opcional) | temperatura da **CPU** — [veja abaixo](#-temperatura-da-cpu-librehardwaremonitor) |

Sem GPU NVIDIA ou sem o LibreHardwareMonitor, o app funciona normalmente — os campos que faltam aparecem como `--`.

## 🚀 Instalação

No **PowerShell**:

```powershell
git clone https://github.com/raphaeloreis/turing-music-clock.git
cd turing-music-clock
.\install.ps1
```

O `install.ps1` instala o Python (se faltar), cria o ambiente virtual (`.venv`), instala as dependências e pergunta se você quer iniciar junto com o Windows.

> Se o PowerShell bloquear o script, rode uma vez:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## ▶️ Rodar

```powershell
.\run.ps1
```

Deixe o display conectado por USB. Se a porta não for detectada automaticamente, ajuste `COM_PORT` (veja abaixo).

## ⚙️ Configuração

No topo do `music-visualizer.py`:

| Parâmetro | Valores | O que faz |
|---|---|---|
| `COM_PORT` | `"AUTO"` ou `"COM5"` | porta serial do display (auto-detecta por padrão) |
| `IDLE_STYLE` | `"digital"` / `"flip"` | estilo do relógio ocioso |
| `TEMP_REFRESH_SEC` | ex. `3` | de quantos em quantos segundos relê os sensores |
| `IDLE_ACCENT` | RGB, ex. `(56, 225, 255)` | cor do relógio digital |

Orientação da tela: no bloco principal, `SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)` — troque por `LANDSCAPE`, `PORTRAIT` ou `REVERSE_PORTRAIT`.

## 🔄 Iniciar com o Windows

```powershell
.\scripts\setup-autostart.ps1
```

Cria uma tarefa agendada (ao logon, +30s, oculta, sem janela). Para remover:

```powershell
Unregister-ScheduledTask -TaskName TuringMusicClock
```

## 🌡️ Temperatura da CPU (LibreHardwareMonitor)

No Windows não dá para ler a temperatura da CPU direto do Python (precisa de um driver de kernel + admin — é o que os apps de monitoramento fazem). A forma confiável é usar o **LibreHardwareMonitor** como fonte:

1. Baixe o [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) (portátil).
2. Rode-o **como administrador** (necessário para ler o sensor da CPU).
3. Em **Options**, marque **Run web server** (porta padrão `8085`) e, se quiser, **Start Minimized** + **Minimize To Tray**.
4. O app lê a temperatura em `http://localhost:8085/data.json`.

Para o LHM subir sozinho no boot **elevado**, crie uma tarefa (em um PowerShell **como administrador**), ajustando o caminho do executável:

```powershell
$exe = "C:\caminho\para\LibreHardwareMonitor\LibreHardwareMonitor.exe"
$me  = "$env:USERDOMAIN\$env:USERNAME"
$action    = New-ScheduledTaskAction    -Execute $exe -WorkingDirectory (Split-Path $exe)
$trigger   = New-ScheduledTaskTrigger   -AtLogOn -User $me
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName "LibreHardwareMonitor" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
```

> A URL/porta pode ser mudada na constante `LHM_URL` no `music-visualizer.py`.

## Créditos

- **Desenvolvedor original:** [mathoudebine](https://github.com/mathoudebine) — [turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) (a base de comunicação com o display).
- **Fork base:** [spel987](https://github.com/spel987) — [turing-3.5-screen-music-visualizer](https://github.com/spel987/turing-3.5-screen-music-visualizer) (o visualizador de música).
- **Este fork:** relógio digital/flip, métricas de CPU/GPU, tela idle, otimizações e instalador.

### Fontes

- [DSEG](https://github.com/keshikan/DSEG) (relógio 7-segmentos) — licença SIL OFL.
- [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) (flip) — licença SIL OFL.
- [Roboto](https://fonts.google.com/specimen/Roboto) — licença Apache 2.0.

## Licença

[GPL-3.0](LICENSE), herdada do projeto original. As fontes mantêm suas respectivas licenças (arquivos em `res/fonts/`).
