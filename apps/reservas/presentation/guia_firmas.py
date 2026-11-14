"""Aceptación electrónica interna y verificable de las guías de práctica."""

from copy import deepcopy
from hashlib import sha256
import hmac
import json

from django.utils import timezone


FIRMA_TIPO = "aceptacion_electronica_interna"
FIRMA_DECLARACION = (
    "Declaro que revisé el contenido académico y los datos automáticos de esta "
    "guía, y que corresponden a la solicitud vinculada."
)


def _contenido_sin_firma(contenido):
    limpio = deepcopy(contenido or {})
    limpio.pop("firma_elaborador", None)
    return limpio


def _huella(*, contenido, guia_id, actividad_id, reserva_id, usuario_id, momento):
    carga = {
        "contenido": _contenido_sin_firma(contenido),
        "guia_id": guia_id,
        "actividad_id": actividad_id,
        "reserva_id": reserva_id,
        "usuario_id": usuario_id,
        "momento": momento,
    }
    serializado = json.dumps(
        carga,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return sha256(serializado.encode("utf-8")).hexdigest()


def firmar_contenido_guia(contenido, *, guia, usuario, reserva=None, momento=None):
    """Registra autor, instante, reserva y huella sin alterar el contenido visible."""
    limpio = _contenido_sin_firma(contenido)
    instante = momento or timezone.now()
    instante_iso = instante.isoformat()
    reserva_id = getattr(reserva, "pk", None) or limpio.get("reserva_fuente_id")
    nombre = usuario.get_full_name().strip() or usuario.username
    firma = {
        "tipo": FIRMA_TIPO,
        "declaracion": FIRMA_DECLARACION,
        "usuario_id": usuario.pk,
        "usuario": usuario.username,
        "nombre": nombre,
        "momento": instante_iso,
        "reserva_id": reserva_id,
        "reserva_codigo": getattr(reserva, "codigo_reserva", "") or limpio.get(
            "reserva_fuente_codigo", ""
        ),
    }
    firma["huella_sha256"] = _huella(
        contenido=limpio,
        guia_id=guia.pk,
        actividad_id=guia.actividad_id,
        reserva_id=reserva_id,
        usuario_id=usuario.pk,
        momento=instante_iso,
    )
    limpio["firma_elaborador"] = firma
    return limpio


def verificar_firma_elaborador(guia):
    contenido = guia.contenido if isinstance(guia.contenido, dict) else {}
    firma = contenido.get("firma_elaborador")
    if not isinstance(firma, dict) or firma.get("tipo") != FIRMA_TIPO:
        return False
    esperado = _huella(
        contenido=contenido,
        guia_id=guia.pk,
        actividad_id=guia.actividad_id,
        reserva_id=firma.get("reserva_id"),
        usuario_id=firma.get("usuario_id"),
        momento=firma.get("momento"),
    )
    return hmac.compare_digest(str(firma.get("huella_sha256", "")), esperado)


# Firmas del FT04: quien elabora firma siempre (aceptación electrónica del
# autor); revisión y aprobación se incluyen solo cuando la guía lo requiere y
# entonces deben llevar nombre y cargo.
ROLES_FIRMA = (
    ("elaborado", "Elaborado por"),
    ("revisado", "Revisado por"),
    ("aprobado", "Aprobado por"),
)
VERDADEROS = {"1", "true", "on", "si", "sí"}


def firmas_predeterminadas(*, legado=False):
    """Roles con sus valores iniciales; ``legado`` conserva las tres columnas."""
    return {
        rol: {"activo": legado or rol == "elaborado", "nombre": "", "cargo": "", "fecha": ""}
        for rol, _etiqueta in ROLES_FIRMA
    }


def normalizar_firmas(valor):
    """``{rol: {activo, nombre, cargo, fecha}}`` desde un dict o su JSON."""
    if isinstance(valor, str):
        valor = valor.strip()
        if valor:
            try:
                valor = json.loads(valor)
            except ValueError as error:
                raise ValueError("Las firmas de la guía no son válidas") from error
        else:
            valor = {}
    if valor is None:
        valor = {}
    if not isinstance(valor, dict):
        raise ValueError("Las firmas de la guía no son válidas")
    firmas = firmas_predeterminadas()
    for rol, base in firmas.items():
        datos = valor.get(rol)
        if not isinstance(datos, dict):
            continue
        base["nombre"] = str(datos.get("nombre") or "").strip()[:180]
        base["cargo"] = str(datos.get("cargo") or "").strip()[:120]
        base["fecha"] = str(datos.get("fecha") or "").strip()[:40]
        activo = datos.get("activo", True)
        if isinstance(activo, str):
            activo = activo.strip().lower() in VERDADEROS
        base["activo"] = rol == "elaborado" or bool(activo)
    return firmas


def firmas_desde_post(datos):
    """Campos ``firma_<rol>_*`` del formulario clásico; ``None`` si no vinieron."""
    if not any(str(clave).startswith("firma_") for clave in datos.keys()):
        return None
    return normalizar_firmas({
        rol: {
            "activo": rol == "elaborado" or str(datos.get(f"firma_{rol}_activo") or "").lower() in VERDADEROS,
            "nombre": datos.get(f"firma_{rol}_nombre", ""),
            "cargo": datos.get(f"firma_{rol}_cargo", ""),
            "fecha": datos.get(f"firma_{rol}_fecha", ""),
        }
        for rol, _etiqueta in ROLES_FIRMA
    })


def firmas_faltantes(firmas):
    """Datos que el autor debe completar en los roles que decidió incluir."""
    etiquetas = dict(ROLES_FIRMA)
    faltantes = []
    for rol, datos in (firmas or {}).items():
        # La persona que elabora siempre queda identificada por el sistema.
        if rol == "elaborado" or not datos.get("activo"):
            continue
        if not datos.get("nombre"):
            faltantes.append(f"{etiquetas.get(rol, rol)}: nombre")
        if not datos.get("cargo"):
            faltantes.append(f"{etiquetas.get(rol, rol)}: cargo")
    return faltantes
