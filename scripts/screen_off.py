# Apaga a tela do Turing Smart Screen 3.5".
# Pensado para rodar como SCRIPT DE DESLIGAMENTO do Windows (contexto SYSTEM),
# depois que o app principal ja foi encerrado -> a porta serial fica livre.
# Tambem serve para rodar manualmente ("apaga a tela agora").
import os
import sys
import time
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

# 1) encerra o app (se estiver rodando) para liberar a COM
try:
    subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe"], capture_output=True)
except Exception:
    pass
time.sleep(1)

# 2) apaga a tela
try:
    from library.lcd.lcd_comm_rev_a import LcdCommRevA
    lcd = LcdCommRevA(com_port="AUTO", display_width=320, display_height=480)
    lcd.Reset()
    lcd.InitializeComm()
    lcd.ScreenOff()
    try:
        lcd.lcd_serial.flush()
    except Exception:
        pass
    lcd.closeSerial()
    print("ScreenOff enviado")
except Exception as e:
    print("falhou:", e)
