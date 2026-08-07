@echo off
REM Apaga a tela (chamado pelo script de desligamento do Windows). Caminhos relativos ao .bat.
"%~dp0..\.venv\Scripts\python.exe" "%~dp0screen_off.py"
