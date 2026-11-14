"""Generador de bienvenida: ilustraciones propias, voz SAPI ES y subtítulos abiertos."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse
import hashlib
import json
import math
import struct
import shutil
import subprocess
import wave

BASE = Path(__file__).resolve().parent
QA = BASE / ".qa"
ASSETS = BASE / "assets"
WIDTH, HEIGHT, FPS = 1280, 720, 24
PALETTE = {
    "navy": "#0a1c27",
    "green": "#225a3d",
    "gold": "#ffda4a",
    "white": "#f6faf7",
    "muted": "#b9d2c6",
    "panel": "#14382f",
}


def font(size, bold=False):
    filename = "arialbd.ttf" if bold else "arial.ttf"
    choices = [
        Path("C:/Windows/Fonts") / filename,
        Path("/usr/share/fonts/truetype/dejavu")
        / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for path in choices:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError("Instale Arial o DejaVu Sans para reproducir las imágenes.")


def wrap(text, draw, selected, maximum):
    result = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            attempt = f"{line} {word}".strip()
            if draw.textlength(attempt, font=selected) > maximum and line:
                result.append(line)
                line = word
            else:
                line = attempt
        result.append(line)
    return result


def block(draw, text, xy, size=36, bold=False, color=None, maximum=730, spacing=12):
    selected = font(size, bold)
    lines = wrap(text, draw, selected, maximum)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=selected, fill=color or PALETTE["white"])
        y += size + spacing
    return y


def arrow(draw, start, end, color=None, width=6):
    color = color or PALETTE["gold"]
    draw.line([start, end], fill=color, width=width)
    x, y = end
    draw.polygon([(x, y), (x - 14, y - 9), (x - 14, y + 9)], fill=color)


def box(draw, x, y, size=72, color=None):
    color = color or PALETTE["gold"]
    draw.rounded_rectangle(
        (x, y, x + size, y + size), radius=12, outline=color, width=5
    )
    draw.line((x + size / 2, y, x + size / 2, y + size / 3), fill=color, width=5)
    draw.line(
        (x + 12, y + size - 17, x + size - 12, y + size - 17), fill=color, width=3
    )


def icon(draw, kind):
    cx, cy = 1014, 280
    draw.ellipse(
        (cx - 146, cy - 146, cx + 146, cy + 146),
        fill=PALETTE["panel"],
        outline="#407c5a",
        width=2,
    )
    if kind in {"welcome", "inventory"}:
        box(draw, 944, 206, 88)
        box(draw, 1004, 304, 62)
        box(draw, 914, 310, 62)
        if kind == "inventory":
            arrow(draw, (1084, 242), (1140, 242))
    elif kind == "start":
        draw.rounded_rectangle(
            (922, 209, 1108, 322), radius=12, outline=PALETTE["gold"], width=6
        )
        draw.line((1015, 324, 1015, 350), fill=PALETTE["gold"], width=6)
        draw.line((970, 350, 1060, 350), fill=PALETTE["gold"], width=6)
        draw.line((960, 254, 994, 282, 1060, 234), fill=PALETTE["white"], width=9)
    elif kind == "assessment":
        draw.rounded_rectangle(
            (943, 185, 1088, 370), radius=15, outline=PALETTE["gold"], width=6
        )
        for y in [226, 275, 324]:
            draw.rectangle((962, y, 980, y + 18), outline=PALETTE["white"], width=3)
            draw.line((992, y + 8, 1065, y + 8), fill=PALETTE["muted"], width=4)
    elif kind == "mcp":
        for x in [918, 1052]:
            draw.rounded_rectangle(
                (x, 235, x + 66, 313), radius=13, outline=PALETTE["gold"], width=5
            )
        draw.line((984, 274, 1052, 274), fill=PALETTE["white"], width=5)
        draw.arc((989, 319, 1038, 369), 180, 360, fill=PALETTE["gold"], width=5)
        draw.rounded_rectangle((984, 343, 1043, 383), radius=8, fill=PALETTE["gold"])
        draw.ellipse((1008, 353, 1019, 366), fill=PALETTE["navy"])
    elif kind == "finish":
        draw.rounded_rectangle(
            (930, 211, 1099, 327), radius=19, outline=PALETTE["gold"], width=6
        )
        draw.polygon([(964, 327), (964, 354), (994, 327)], fill=PALETTE["gold"])
        for x in [965, 1009, 1053]:
            draw.ellipse((x, 259, x + 12, 271), fill=PALETTE["white"])


def render_scene(scene, index):
    image = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["navy"])
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        mix = y / HEIGHT
        draw.line(
            (0, y, WIDTH, y),
            fill=(10 + int(mix * 5), 28 + int(mix * 25), 39 + int(mix * 8)),
        )
    draw.rounded_rectangle((54, 40, 285, 78), radius=18, fill=PALETTE["green"])
    draw.text(
        (73, 50), "VIDEO DE BIENVENIDA", font=font(16, True), fill=PALETTE["gold"]
    )
    draw.text(
        (798, 50),
        "Laboratorio de Logística · UPEC",
        font=font(20),
        fill=PALETTE["muted"],
    )
    draw.text((60, 111), scene["label"], font=font(18, True), fill=PALETTE["gold"])
    block(draw, scene["title"], (58, 151), size=48, bold=True, maximum=760)
    block(
        draw,
        scene["body"],
        (61, 286),
        size=29,
        maximum=720,
        spacing=15,
        color=PALETTE["muted"],
    )
    kind = scene["type"]
    if kind not in {"route", "study"}:
        icon(draw, kind)
    if kind == "route":
        words = [
            ("1", "Diseña", "Problema y pantallas"),
            ("2", "Prepara", "Herramientas y guía"),
            ("3", "Construye", "Funciones logísticas"),
            ("4", "Conecta", "Datos, IA y MCP"),
            ("5", "Comprueba", "Pruebas y proyecto"),
        ]
        for i, (number, name, desc) in enumerate(words):
            x = 60 + i * 236
            draw.rounded_rectangle(
                (x, 373, x + 220, 510),
                radius=18,
                fill=PALETTE["panel"],
                outline="#3d7154",
                width=2,
            )
            draw.text((x + 16, 386), number, font=font(28, True), fill=PALETTE["gold"])
            draw.text((x + 52, 390), name, font=font(23, True), fill=PALETTE["white"])
            block(
                draw,
                desc,
                (x + 16, 441),
                size=17,
                maximum=185,
                spacing=7,
                color=PALETTE["muted"],
            )
    elif kind == "study":
        for i, word in enumerate(["Lee", "Mira", "Practica", "Verifica", "Entrega"]):
            x = 60 + i * 236
            draw.rounded_rectangle(
                (x, 377, x + 220, 490),
                radius=18,
                fill=PALETTE["panel"],
                outline="#3d7154",
                width=2,
            )
            draw.ellipse((x + 17, 398, x + 59, 440), fill=PALETTE["gold"])
            draw.text(
                (x + 30, 406), str(i + 1), font=font(20, True), fill=PALETTE["navy"]
            )
            draw.text((x + 73, 404), word, font=font(25, True), fill=PALETTE["white"])
    else:
        chips = {
            "welcome": ["40 horas", "5 unidades", "Tu proyecto"],
            "start": ["Plantilla guiada", "Pasos sencillos", "Cambios pequeños"],
            "inventory": ["Datos ficticios", "Reglas comprobables", "Historial claro"],
            "assessment": ["70 % en quizzes", "3 intentos", "Revisión docente"],
            "mcp": ["Conexión preparada", "Sólo lectura", "Contrasta los datos"],
            "finish": ["Pausa", "Pide ayuda", "Conserva una versión"],
        }[kind]
        for i, chip in enumerate(chips):
            x = 60 + i * 267
            draw.rounded_rectangle(
                (x, 441, x + 250, 495),
                radius=16,
                fill=PALETTE["panel"],
                outline="#3d7154",
                width=1,
            )
            draw.text((x + 16, 458), chip, font=font(19, True), fill=PALETTE["white"])
    draw.text(
        (61, 684),
        "Narración sintética en español · Material introductorio propio",
        font=font(15),
        fill=PALETTE["muted"],
    )
    draw.text(
        (1128, 682), f"{index + 1} / 8", font=font(20, True), fill=PALETTE["gold"]
    )
    for i in range(8):
        x = 60 + i * 147
        draw.rounded_rectangle(
            (x, 709, x + 134, 714),
            radius=2,
            fill=PALETTE["gold"] if i <= index else "#315446",
        )
    return image


def timestamp(seconds, separator="."):
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{separator}{millis:03}"


def captions(text, duration, offset):
    # Agrupa frases breves; reparto proporcional de tiempo a palabras de la voz sintetizada.
    words = text.split()
    groups = []
    current = []
    for word in words:
        current.append(word)
        if len(current) >= 15 or (len(current) >= 7 and word.endswith((".", ":", ";"))):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    result, elapsed = [], 0.0
    for group in groups:
        part = duration * len(group) / len(words)
        result.append((offset + elapsed, offset + elapsed + part, " ".join(group)))
        elapsed += part
    return result


def execute(command, **kwargs):
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kwargs,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr[-3000:])
    return completed


def movie_duration(path):
    """Lee la duración exacta de la cabecera mvhd del contenedor MP4."""
    data = path.read_bytes()

    def boxes(start, end):
        while start + 8 <= end:
            size, kind = struct.unpack_from(">I4s", data, start)
            header = 8
            if size == 1:
                size = struct.unpack_from(">Q", data, start + 8)[0]
                header = 16
            if size == 0:
                size = end - start
            if size < header or start + size > end:
                raise ValueError("Cabecera MP4 inválida.")
            yield kind, start + header, start + size
            start += size

    for kind, start, end in boxes(0, len(data)):
        if kind == b"moov":
            for sub, first, _ in boxes(start, end):
                if sub == b"mvhd":
                    version = data[first]
                    offset = first + (20 if version else 12)
                    scale = struct.unpack_from(">I", data, offset)[0]
                    count = struct.unpack_from(
                        ">Q" if version else ">I", data, offset + 4
                    )[0]
                    if scale <= 0:
                        raise ValueError("Escala temporal MP4 inválida.")
                    return count / scale
    raise ValueError("No se encontró la duración del contenedor MP4.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--public-dir", type=Path)
    args = parser.parse_args()
    ASSETS.mkdir(exist_ok=True)
    (QA / "frames").mkdir(parents=True, exist_ok=True)
    (QA / "clips").mkdir(parents=True, exist_ok=True)
    scenes = json.loads((BASE / "escenas.json").read_text(encoding="utf-8"))
    all_cues, timeline, total = [], [], 0
    for i, scene in enumerate(scenes):
        wav = QA / "audio" / f"escena-{i + 1:02}.wav"
        with wave.open(str(wav)) as audio:
            audio_duration = audio.getnframes() / audio.getframerate()
        length = math.ceil(audio_duration + 1.25)
        timeline.append(
            {
                "escena": i + 1,
                "inicio": total,
                "duracion": length,
                "voz_segundos": audio_duration,
                "titulo": scene["title"],
            }
        )
        local_cues = captions(scene["narration"], audio_duration, 0.5)
        all_cues.extend(
            (start + total, end + total, text) for start, end, text in local_cues
        )
        frame = render_scene(scene, i)
        image_path = QA / "frames" / f"escena-{i + 1:02}.png"
        frame.save(image_path)
        srt = QA / "frames" / f"escena-{i + 1:02}.srt"
        srt.write_text(
            "\n\n".join(
                f"{n + 1}\n{timestamp(a, ',')} --> {timestamp(b, ',')}\n{text}"
                for n, (a, b, text) in enumerate(local_cues)
            )
            + "\n",
            encoding="utf-8",
        )
        clip = QA / "clips" / f"escena-{i + 1:02}.mp4"
        # Subtítulos abiertos y fundidos sencillos; texto principal siempre estable y legible.
        subtitle_filter = f"subtitles=escena-{i + 1:02}.srt:force_style='FontName=Arial,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101C16,BackColour=&HCC0A1C27,BorderStyle=3,Outline=2,Shadow=0,MarginV=30,MarginL=60,MarginR=60,Alignment=2'"
        filters = f"{subtitle_filter},fade=t=in:st=0:d=0.35,fade=t=out:st={length - 0.35}:d=0.35,format=yuv420p"
        execute(
            [
                args.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-i",
                str(image_path),
                "-i",
                str(wav),
                "-vf",
                filters,
                "-af",
                f"adelay=500:all=1,apad,atrim=duration={length},loudnorm=I=-16:TP=-1.5:LRA=11",
                "-t",
                str(length),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-ar",
                "44100",
                "-ac",
                "1",
                "-r",
                str(FPS),
                str(clip),
            ],
            cwd=QA / "frames",
        )
        total += length
        print(f"Escena {i + 1}/8 terminada ({length} s).", flush=True)
    concat = QA / "clips" / "lista.txt"
    concat.write_text(
        "\n".join(f"file 'escena-{i + 1:02}.mp4'" for i in range(len(scenes))) + "\n",
        encoding="utf-8",
    )
    video = ASSETS / "bienvenida-logistica-ia.mp4"
    execute(
        [
            args.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "-metadata",
            "title=Bienvenida: tu ruta para crear una aplicación logística",
            "-metadata",
            "comment=Material original; voz sintética Microsoft Sabina es-MX; datos ficticios.",
            str(video),
        ]
    )
    vtt = (
        "WEBVTT\n\n"
        + "\n\n".join(
            f"{i + 1}\n{timestamp(start)} --> {timestamp(end)}\n{text}"
            for i, (start, end, text) in enumerate(all_cues)
        )
        + "\n"
    )
    (ASSETS / "bienvenida-es.vtt").write_text(vtt, encoding="utf-8")
    poster = render_scene(scenes[0], 0)
    d = ImageDraw.Draw(poster)
    d.rounded_rectangle((60, 548, 800, 633), radius=20, fill=PALETTE["green"])
    d.polygon([(88, 568), (88, 611), (125, 589)], fill=PALETTE["gold"])
    d.text(
        (148, 573),
        "Bienvenida · Conoce tu ruta de estudio",
        font=font(27, True),
        fill=PALETTE["white"],
    )
    poster.save(ASSETS / "bienvenida-poster.png")
    transcript = (
        "# Bienvenida: tu ruta para crear una aplicación logística\n\nNarración original sintetizada en español (Microsoft Sabina, es-MX).\n\n"
        + "\n\n".join(
            f"## {i + 1}. {scene['title']}\n\n{scene['narration']}"
            for i, scene in enumerate(scenes)
        )
        + "\n"
    )
    (BASE / "transcripcion.md").write_text(transcript, encoding="utf-8")
    metadata = {
        "filename": video.name,
        "duration_seconds": movie_duration(video),
        "timeline_seconds": total,
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "audio": "AAC mono, narración sintética española Microsoft Sabina (es-MX)",
        "voice_rate_sapi": 1,
        "video": "H.264 yuv420p, faststart",
        "study_minutes": 5,
        "open_captions": True,
        "subtitle_timing": "Bloques de palabras repartidos proporcionalmente dentro del audio de cada escena.",
        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "bytes": video.stat().st_size,
        "scenes": timeline,
    }
    (BASE / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.public_dir:
        args.public_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            ASSETS / "bienvenida-poster.png", args.public_dir / "bienvenida-poster.png"
        )
        shutil.copyfile(
            ASSETS / "bienvenida-es.vtt", args.public_dir / "bienvenida-es.vtt"
        )
    print(
        json.dumps(
            {
                "duracion_segundos": metadata["duration_seconds"],
                "bytes": metadata["bytes"],
                "sha256": metadata["sha256"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
