"""Entrega el video original ya generado, sin codificarlo en peticiones web."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WELCOME_FILENAME = "bienvenida-logistica-ia.mp4"
WELCOME_POSTER_STATIC = "portal/img/cursos/logistica-ia/bienvenida-poster.png"
WELCOME_SUBTITLES_STATIC = "portal/img/cursos/logistica-ia/bienvenida-es.vtt"
WELCOME_STUDY_MINUTES = 5


def get_welcome_video() -> bytes:
    return (BASE_DIR / "assets" / WELCOME_FILENAME).read_bytes()


def get_welcome_metadata() -> dict:
    return json.loads((BASE_DIR / "metadata.json").read_text(encoding="utf-8"))
