"""Identidad revisable y huellas estables, sin Django ni acceso a datos."""

from hashlib import sha256
import json


CAMPOS_IDENTIDAD = (
    'usuario_id', 'nombre', 'apellidos', 'correo', 'tipo_usuario',
    'institucion', 'facultad', 'carrera', 'documento',
)


def identidad_revisable(institucion_codigo, datos):
    """Lista permitida: excluye contraseña, teléfono, avatar y nivel periódico."""
    return {
        'version': 1,
        'institucion_codigo': str(institucion_codigo).strip(),
        **{campo: str(datos.get(campo) or '').strip() for campo in CAMPOS_IDENTIDAD},
    }


def huella_revision(identidad, ultima_decision=None):
    contenido = json.dumps(
        {'identidad': identidad, 'ultima_decision': ultima_decision},
        sort_keys=True, ensure_ascii=True, separators=(',', ':'),
    )
    return sha256(contenido.encode('utf-8')).hexdigest()
