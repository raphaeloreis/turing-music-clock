from library.lcd.lcd_comm import Orientation
from library.lcd.lcd_comm_rev_a import LcdCommRevA
from asyncio import run
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
from winrt.windows.storage.streams import DataReader, Buffer, InputStreamOptions
from os import name
from os.path import dirname, abspath, join
import signal
from time import sleep, perf_counter
from library.log import logger
from io import BytesIO
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from datetime import datetime
import json
import subprocess
import urllib.request
import psutil
import serial

COM_PORT = "AUTO"
REVISION = "A"
IDLE_STYLE = "digital"  # tela ociosa: "digital" (relogio 7-seg) ou "flip" (painel de aeroporto)
stop = False
script_dir = dirname(abspath(__file__))

font_bold = ImageFont.truetype(join(script_dir, "res", "fonts", "roboto", "Roboto-Black.ttf"), 28)
font_light = ImageFont.truetype(join(script_dir, "res", "fonts", "roboto", "Roboto-Medium.ttf"), 26)
font_light_small = ImageFont.truetype(join(script_dir, "res", "fonts", "roboto", "Roboto-Medium.ttf"), 22)
font_temp = ImageFont.truetype(join(script_dir, "res", "fonts", "roboto", "Roboto-Medium.ttf"), 18)

# --- Tela idle: relogio digital + metricas (tema escuro) --------------------
dseg_big   = ImageFont.truetype(join(script_dir, "res", "fonts", "dseg", "DSEG7Classic-Bold.ttf"), 96)
dseg_val   = ImageFont.truetype(join(script_dir, "res", "fonts", "dseg", "DSEG7Classic-Bold.ttf"), 30)
idle_label = ImageFont.truetype(join(script_dir, "res", "fonts", "roboto", "Roboto-Medium.ttf"), 22)
idle_unit  = ImageFont.truetype(join(script_dir, "res", "fonts", "roboto", "Roboto-Medium.ttf"), 20)
idle_date_font = ImageFont.truetype(join(script_dir, "res", "fonts", "roboto", "Roboto-Medium.ttf"), 22)
IDLE_ACCENT = (56, 225, 255)   # cor "acesa" do relogio (ciano) - troque aqui p/ mudar o tema
IDLE_GHOST  = (20, 48, 60)     # segmentos apagados do display
IDLE_MUTED  = (120, 140, 165)  # rotulos/data
_WD = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
_MO = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

def _make_idle_bg():
    top, bot = (12, 17, 24), (4, 6, 10)
    col = Image.new("RGB", (1, 320))
    for y in range(320):
        f = y / 319
        col.putpixel((0, y), tuple(int(top[i] + (bot[i] - top[i]) * f) for i in range(3)))
    return col.resize((480, 320))

_IDLE_BG = _make_idle_bg()

def _temp_color(t):
    if t is None: return IDLE_MUTED
    if t < 55: return (70, 220, 150)
    if t < 70: return (255, 185, 50)
    return (255, 85, 85)

# --- Sensores: temperatura + uso --------------------------------------------
# CPU temp: LibreHardwareMonitor (rodar COMO ADMIN com "Run web server").
# CPU uso: psutil. GPU temp+uso: nvidia-smi (driver ja instalado).
LHM_URL = "http://localhost:8085/data.json"
TEMP_REFRESH_SEC = 3  # o loop desenha a cada 1s; relemos os sensores a cada 3s
_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # nao pisca console sob pythonw
psutil.cpu_percent(interval=None)  # prime: 1a leitura serve de baseline
_stats_cache = {"cpu_temp": None, "cpu_use": None, "gpu_temp": None, "gpu_use": None, "ts": None}

def _parse_temp(value):
    try:
        return float(str(value).split()[0].replace(",", "."))
    except (ValueError, IndexError):
        return None

def _find_cpu_temp(node, in_cpu=False, best=None):
    text = node.get("Text") or ""
    if any(hint in text for hint in ("Ryzen", "AMD", "CPU")):
        in_cpu = True
    value = node.get("Value") or ""
    if in_cpu and "°C" in value:
        low = text.lower()
        if "tctl" in low or "tdie" in low:
            rank = 3
        elif "package" in low:
            rank = 2
        elif "core" in low:
            rank = 1
        else:
            rank = 0
        temp = _parse_temp(value)
        if temp is not None and (best is None or rank > best[0]):
            best = (rank, temp)
    for child in (node.get("Children") or []):
        best = _find_cpu_temp(child, in_cpu, best)
    return best

def read_cpu_temp():
    try:
        with urllib.request.urlopen(LHM_URL, timeout=1.0) as resp:
            data = json.load(resp)
    except Exception:
        return None
    best = _find_cpu_temp(data)
    return best[1] if best else None

def read_cpu_usage():
    try:
        return psutil.cpu_percent(interval=None)
    except Exception:
        return None

def read_gpu_stats():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2.0, creationflags=_no_window,
        )
        if out.returncode == 0:
            parts = out.stdout.strip().splitlines()[0].split(",")
            temp = _parse_temp(parts[0])
            use = _parse_temp(parts[1]) if len(parts) > 1 else None
            return temp, use
    except Exception:
        pass
    return None, None

def get_stats():
    now = perf_counter()
    if _stats_cache["ts"] is None or now - _stats_cache["ts"] >= TEMP_REFRESH_SEC:
        _stats_cache["cpu_temp"] = read_cpu_temp()
        _stats_cache["cpu_use"] = read_cpu_usage()
        _stats_cache["gpu_temp"], _stats_cache["gpu_use"] = read_gpu_stats()
        _stats_cache["ts"] = now
    return _stats_cache

def draw_idle_screen():
    now = datetime.now()
    stats = get_stats()
    img = _IDLE_BG.copy()
    draw = ImageDraw.Draw(img)

    hhmm = now.strftime("%H:%M")
    date_str = f"{_WD[now.weekday()]}, {now.day} {_MO[now.month - 1]}"

    clock_y = 34
    bb = draw.textbbox((0, 0), "88:88", font=dseg_big)
    cx = (480 - (bb[2] - bb[0])) // 2 - bb[0]

    # glow neon atras do relogio
    glow = Image.new("RGBA", (480, 320), (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((cx, clock_y), hhmm, font=dseg_big, fill=IDLE_ACCENT + (255,))
    glow = glow.filter(ImageFilter.GaussianBlur(9))
    img.paste(glow, (0, 0), glow)

    # segmentos apagados (ghost) + hora por cima
    draw.text((cx, clock_y), "88:88", font=dseg_big, fill=IDLE_GHOST)
    draw.text((cx, clock_y), hhmm, font=dseg_big, fill=IDLE_ACCENT)

    # data centralizada
    bbd = draw.textbbox((0, 0), date_str, font=idle_date_font)
    dx = (480 - (bbd[2] - bbd[0])) // 2 - bbd[0]
    draw.text((dx, 150), date_str, font=idle_date_font, fill=IDLE_MUTED)

    draw.line((60, 196, 420, 196), fill=(30, 40, 52), width=2)

    def row(y, label, t_val, u_val):
        t_s = f"{t_val:02.0f}" if t_val is not None else "--"
        u_s = f"{u_val:02.0f}" if u_val is not None else "--"
        t_font = dseg_val if t_val is not None else idle_unit
        u_font = dseg_val if u_val is not None else idle_unit
        LG, UG, SG = 16, 4, 30
        lw  = draw.textlength(label, font=idle_label)
        tw_ = draw.textlength(t_s, font=t_font)
        dcw = draw.textlength("°C", font=idle_unit)
        uw_ = draw.textlength(u_s, font=u_font)
        pcw = draw.textlength("%", font=idle_unit)
        total = lw + LG + tw_ + UG + dcw + SG + uw_ + UG + pcw
        x = (480 - total) // 2
        tc = _temp_color(t_val)
        uc = IDLE_ACCENT if u_val is not None else IDLE_MUTED
        draw.text((x, y), label, font=idle_label, fill=IDLE_MUTED); x += lw + LG
        draw.text((x, y - 2), t_s, font=t_font, fill=tc);          x += tw_ + UG
        draw.text((x, y + 2), "°C", font=idle_unit, fill=tc);      x += dcw + SG
        draw.text((x, y - 2), u_s, font=u_font, fill=uc);          x += uw_ + UG
        draw.text((x, y + 2), "%", font=idle_unit, fill=uc)

    row(216, "CPU", stats["cpu_temp"], stats["cpu_use"])
    row(262, "GPU", stats["gpu_temp"], stats["gpu_use"])
    return img

# --- Tela idle 2: relogio flip / painel de aeroporto (split-flap) -----------
flip_clock_font = ImageFont.truetype(join(script_dir, "res", "fonts", "bebas", "BebasNeue-Regular.ttf"), 108)
flip_val_font   = ImageFont.truetype(join(script_dir, "res", "fonts", "bebas", "BebasNeue-Regular.ttf"), 48)
flip_label_font = ImageFont.truetype(join(script_dir, "res", "fonts", "bebas", "BebasNeue-Regular.ttf"), 34)
flip_unit_font  = ImageFont.truetype(join(script_dir, "res", "fonts", "bebas", "BebasNeue-Regular.ttf"), 30)
flip_date_font  = ImageFont.truetype(join(script_dir, "res", "fonts", "bebas", "BebasNeue-Regular.ttf"), 34)
FLIP_CARD     = (26, 26, 31)
FLIP_CARD_TOP = (40, 40, 47)
FLIP_SEAM     = (8, 8, 10)
FLIP_CHAR     = (240, 235, 224)

def _flip_tile(draw, x, y, w, h, ch, font):
    r = max(6, h // 12)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=r, fill=FLIP_CARD)
    mid = y + h // 2
    draw.rounded_rectangle((x, y, x + w, mid + r), radius=r, fill=FLIP_CARD_TOP)  # topo mais claro
    draw.rectangle((x, mid, x + w, mid + r), fill=FLIP_CARD_TOP)
    if ch:
        bb = draw.textbbox((0, 0), ch, font=font)
        cw, chh = bb[2] - bb[0], bb[3] - bb[1]
        draw.text((x + (w - cw) // 2 - bb[0], y + (h - chh) // 2 - bb[1]), ch, font=font, fill=FLIP_CHAR)
    draw.rectangle((x, mid - 1, x + w, mid + 1), fill=FLIP_SEAM)  # fenda das abas

def draw_flip_screen():
    now = datetime.now()
    stats = get_stats()
    hhmm = now.strftime("%H:%M")
    img = _IDLE_BG.copy()
    draw = ImageDraw.Draw(img)

    # relogio grande: [H][H] : [M][M]
    tw, th, gap, sg, cg = 80, 102, 8, 12, 26
    y0 = 20
    x = 47
    _flip_tile(draw, x, y0, tw, th, hhmm[0], flip_clock_font); x += tw + gap
    _flip_tile(draw, x, y0, tw, th, hhmm[1], flip_clock_font); x += tw + sg
    colx = x + cg // 2
    for cy in (y0 + th // 3, y0 + 2 * th // 3):
        draw.ellipse((colx - 6, cy - 6, colx + 6, cy + 6), fill=FLIP_CHAR)
    x += cg + sg
    _flip_tile(draw, x, y0, tw, th, hhmm[3], flip_clock_font); x += tw + gap
    _flip_tile(draw, x, y0, tw, th, hhmm[4], flip_clock_font)

    # data como etiqueta (texto simples, estilo legenda de painel), sem tile
    date_str = f"{_WD[now.weekday()]}  {now.day:02d}  {_MO[now.month - 1]}"
    dw = draw.textlength(date_str, font=flip_date_font)
    draw.text(((480 - dw) // 2, 136), date_str, font=flip_date_font, fill=IDLE_MUTED)

    # linhas CPU / GPU com mini-tiles (bloco inteiro centralizado)
    stw, sth, sgp = 40, 50, 6
    LABEL_GAP, UNIT_GAP, SEC_GAP = 16, 5, 28

    def _field_w(s):
        return len(s) * stw + (len(s) - 1) * sgp

    def _draw_field(x, y, s):
        for ch in s:
            _flip_tile(draw, x, y, stw, sth, ch, flip_val_font)
            x += stw + sgp
        return x - sgp  # sem o gap final

    def row(y, label, t_val, u_val):
        cy = y + sth // 2
        ts = f"{t_val:02.0f}" if t_val is not None else "--"
        us = f"{u_val:02.0f}" if u_val is not None else "--"
        lw = draw.textlength(label, font=flip_label_font)
        dw = draw.textlength("°C", font=flip_unit_font)
        pw = draw.textlength("%", font=flip_unit_font)
        total = lw + LABEL_GAP + _field_w(ts) + UNIT_GAP + dw + SEC_GAP + _field_w(us) + UNIT_GAP + pw
        x = (480 - total) // 2

        def vtext(tx, text, font):
            bb = draw.textbbox((0, 0), text, font=font)
            draw.text((tx, cy - (bb[3] - bb[1]) // 2 - bb[1]), text, font=font, fill=IDLE_MUTED)

        vtext(x, label, flip_label_font)
        x += lw + LABEL_GAP
        x = _draw_field(x, y, ts) + UNIT_GAP
        vtext(x, "°C", flip_unit_font)
        x += dw + SEC_GAP
        x = _draw_field(x, y, us) + UNIT_GAP
        vtext(x, "%", flip_unit_font)

    row(186, "CPU", stats["cpu_temp"], stats["cpu_use"])
    row(250, "GPU", stats["gpu_temp"], stats["gpu_use"])
    return img

def render_idle():
    if IDLE_STYLE == "flip":
        return draw_flip_screen()
    return draw_idle_screen()

async def get_media_info(retries=3):
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    if current_session:
        info = await current_session.try_get_media_properties_async()
        status = current_session.get_playback_info().playback_status.name
        if info:
            for _ in range(retries):
                thumbnail = info.thumbnail
                if thumbnail:
                    return {
                        "title": info.title,
                        "artist": info.artist,
                        "album_title": info.album_title,
                        "thumbnail": thumbnail,
                        "status": status
                    }
            return {
                "title": info.title,
                "artist": info.artist,
                "album_title": info.album_title,
                "thumbnail": None,
                "status": status
            }
    return None

async def read_stream_into_buffer(stream_ref, buffer):
    readable_stream = await stream_ref.open_read_async()
    await readable_stream.read_async(buffer, buffer.capacity, InputStreamOptions.READ_AHEAD)

def get_dominant_and_inverse_color(image, factor=1.2):
    image = image.convert("RGB")
    image = image.resize((100, 100))
    colors = image.getcolors(image.width * image.height)
    dominant_color = max(colors, key=lambda item: item[0])[1]

    r = min(int(dominant_color[0] * factor), 255)
    g = min(int(dominant_color[1] * factor), 255)
    b = min(int(dominant_color[2] * factor), 255)

    brightened_color = (r, g, b)
    inverse_color = (255 - r, 255 - g, 255 - b)

    return brightened_color, inverse_color


def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        w = font.getlength(' '.join(current_line))
        if w > max_width:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
            
            if len(lines) == 3:
                if current_line or word != words[-1]:
                    last_line = lines[-1]
                    while font.getlength(last_line + "...") > max_width:
                        last_words = last_line.split()
                        last_line = ' '.join(last_words[:-1])
                    lines[-1] = last_line + "..."
                return lines[:3]
    
    if current_line:
        lines.append(' '.join(current_line))
        if len(lines) > 3:
            lines = lines[:2]
            last_line = lines[-1]
            while font.getlength(last_line + "...") > max_width:
                last_words = last_line.split()
                last_line = ' '.join(last_words[:-1])
            lines[-1] = last_line + "..."
            return lines[:3]
    
    return lines

def colored_image(path, width, height, color):
    image = Image.open(path).resize((width, height), Image.LANCZOS).convert("RGBA")
    r, g, b, alpha = image.split()
    colored_image = Image.new("RGBA", image.size, color=color)
    colored_image.putalpha(alpha)
    return colored_image

def save_combined_thumbnail(thumbnail_data=None, title=None, artist=None, album_title=None, status=None):
    screen_width = 480
    screen_height = 320

    time = datetime.now().strftime("%H:%M")

    if thumbnail_data:
        image = Image.open(BytesIO(thumbnail_data))
    else:
        image = Image.open(join(script_dir, "res", "unknown.jpg"))

    brightened_color, inverse_color = get_dominant_and_inverse_color(image)

    blurred = image.copy()
    blurred = blurred.filter(ImageFilter.GaussianBlur(radius=60))

    image_ratio = image.width / image.height
    screen_ratio = screen_width / screen_height

    if image_ratio > screen_ratio:
        new_height = screen_height
        new_width = int(screen_height * image_ratio)
    else:
        new_width = screen_width
        new_height = int(screen_width / image_ratio)

    blurred = blurred.resize((new_width, new_height), Image.LANCZOS)

    dark_overlay = Image.new("RGBA", (screen_width, screen_height), (0, 0, 0, 40))

    blurred_background = Image.new("RGB", (screen_width, screen_height), (255, 255, 255))
    blurred_background.paste(blurred, ((screen_width - blurred.width) // 2, (screen_height - blurred.height) // 2))
    blurred_background.paste(dark_overlay, (0, 0), dark_overlay)

    target_size = 175

    if image_ratio > 1:
        new_height = target_size
        new_width = int(target_size * image_ratio)
    else:
        new_width = 175
        new_height = int(target_size / image_ratio)

    original = image.resize((new_width, new_height), Image.LANCZOS)

    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    right = left + target_size
    bottom = top + target_size
    cropped_image = original.crop((left, top, right, bottom))

    rounded_mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(rounded_mask)
    draw.rounded_rectangle((0, 0, target_size, target_size), 15, fill=255)

    rounded_image = cropped_image.convert("RGBA")
    rounded_image.putalpha(rounded_mask)

    if status == "PAUSED":
        colored_pause = colored_image(join(script_dir, "res", "icons", "pause.png"), 80, 80, inverse_color)
        rounded_image.paste(colored_pause, (45, 45), colored_pause)
        rounded_image.paste(dark_overlay, (0, 0), dark_overlay)

    spotlight = Image.new("RGBA", (325, 325), brightened_color + (100,))

    mask = Image.new("L", (325, 325), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((35, 75, 230, 250), fill=255)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=50))

    spotlight.putalpha(mask)

    blurred_background.paste(spotlight, (-20, -10), spotlight)

    colored_clock = colored_image(join(script_dir, "res", "icons", "clock.png"), 25, 25, inverse_color)

    combined = blurred_background.copy()
    combined.paste(rounded_image, (40, 72), rounded_image)
    combined.paste(colored_clock, (363, 275), colored_clock)

    draw = ImageDraw.Draw(combined)
    max_width = 220

    if title:
        title_lines = wrap_text(title, font_bold, max_width)
        y = 80
        for line in title_lines:
            draw.text((240, y), line, font=font_bold, fill=inverse_color)
            y += 30

    if artist:
        if album_title:
            artist_lines = wrap_text(f"{artist} ({album_title})", font_light, max_width)
        else:
            artist_lines = wrap_text(artist, font_light, max_width)
        y += 10
        for line in artist_lines:
            draw.text((240, y), line, font=font_light, fill=inverse_color)
            y += 30

    draw.text((398, 274), str(time), font=font_light_small, fill=inverse_color)

    stats = get_stats()
    cpu_t = f"{stats['cpu_temp']:.0f}°" if stats['cpu_temp'] is not None else "--"
    cpu_u = f"{stats['cpu_use']:.0f}%" if stats['cpu_use'] is not None else "--"
    gpu_t = f"{stats['gpu_temp']:.0f}°" if stats['gpu_temp'] is not None else "--"
    gpu_u = f"{stats['gpu_use']:.0f}%" if stats['gpu_use'] is not None else "--"
    # Faixa inferior: CPU (temp+uso) . GPU (temp+uso) . relogio (dir, ja desenhado)
    draw.text((40, 280), f"CPU {cpu_t} {cpu_u}", font=font_temp, fill=inverse_color)
    draw.text((200, 280), f"GPU {gpu_t} {gpu_u}", font=font_temp, fill=inverse_color)

    return combined

if __name__ == "__main__":

    def sighandler(signum, frame):
        global stop
        stop = True

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    is_posix = name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, sighandler)

    RECONNECT_WAIT = 3  # segundos entre tentativas de reconexao ao display

    def connect_lcd():
        logger.info("Selected Hardware Revision A (Turing Smart Screen 3.5\" & UsbPCMonitor 3.5\"/5\")")
        lcd = LcdCommRevA(com_port=COM_PORT, display_width=320, display_height=480)
        lcd.Reset()
        lcd.InitializeComm()
        lcd.SetBrightness(level=50)
        lcd.SetBackplateLedColor(led_color=(255, 255, 255))
        lcd.SetOrientation(orientation=Orientation.REVERSE_LANDSCAPE)
        return lcd

    lcd_comm = None
    last_frame = None

    while not stop:
        # (re)conecta ao display se necessario (ex.: cabo desconectado e religado)
        if lcd_comm is None:
            try:
                lcd_comm = connect_lcd()
                last_frame = None  # forca redesenho ao (re)conectar
                logger.info("Display conectado.")
            except (serial.SerialException, OSError) as e:
                logger.error(f"Display indisponivel ({e}). Nova tentativa em {RECONNECT_WAIT}s...")
                sleep(RECONNECT_WAIT)
                continue

        start = perf_counter()
        media_info = run(get_media_info())
        if media_info:

            title = media_info['title']
            artist = media_info['artist']
            album_title = media_info['album_title']
            thumbnail_stream = media_info['thumbnail']
            status = media_info['status']

            if thumbnail_stream:
                thumb_read_buffer = Buffer(5000000)

                run(read_stream_into_buffer(thumbnail_stream, thumb_read_buffer))

                buffer_reader = DataReader.from_buffer(thumb_read_buffer)
                thumbnail_byte_buffer = buffer_reader.read_buffer(thumb_read_buffer.length)
                combined_image = save_combined_thumbnail(thumbnail_byte_buffer, title, artist, album_title, status)
            else:
                combined_image = save_combined_thumbnail(None, title, artist, album_title, status)

        else:
            combined_image = render_idle()

        # so reenvia pra tela se a imagem mudou (evita refresh visivel a toa)
        frame = combined_image.tobytes()
        if frame != last_frame:
            try:
                lcd_comm.DisplayPILImage(combined_image)
                last_frame = frame
                logger.debug(f"refresh done (took {perf_counter() - start:.3f} s)")
            except (serial.SerialException, OSError) as e:
                # cabo caiu no meio do envio -> descarta a conexao e reconecta no proximo ciclo
                logger.error(f"Conexao com o display caiu ({e}). Reconectando...")
                try:
                    lcd_comm.closeSerial()
                except Exception:
                    pass
                lcd_comm = None
                continue

        sleep(1)

    if lcd_comm is not None:
        lcd_comm.closeSerial()