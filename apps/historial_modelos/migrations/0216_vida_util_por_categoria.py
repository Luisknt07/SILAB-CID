"""Vida útil de referencia para los equipos de fabricación digital.

La institución necesita un punto de partida: sin él, el seguimiento no puede
decir cuándo un equipo cumple su vida útil. Estos valores son los que se usan
como referencia para el laboratorio de manufactura digital y prototipado, por
categoría de equipo; cada activo puede ajustar los suyos desde su ficha.

Un equipo llega al fin de su vida útil por tiempo (los años), por uso (las
horas de operación acumuladas) o por daño irreparable, lo que ocurra primero.
"""

from django.db import migrations

# palabras clave en la categoría o el nombre, años de referencia, horas de uso
REFERENCIAS = (
    (('impresión 3d', 'impresora 3d', 'fdm'), 8, 12000),
    (('resina', 'sla'), 6, 6000),
    (('láser', 'laser', 'corte y grabado'), 10, 15000),
    (('cnc', 'mecanizado', 'fresadora'), 12, 20000),
    (('escáner', 'escaner', 'digitalización', 'digitalizacion'), 7, 8000),
    (('computación', 'computacion', 'computadora', 'estación de diseño', 'cad'), 5, 20000),
    (('electrónica', 'electronica', 'instrumentación', 'instrumentacion', 'soldadura'), 10, 10000),
    (('vinilo', 'plotter'), 8, 10000),
    (('secador', 'curado', 'lavado', 'apoyo'), 8, 10000),
)


def _referencia(textos):
    for claves, anios, horas in REFERENCIAS:
        for texto in textos:
            if any(clave in texto for clave in claves):
                return anios, horas
    return None


def sembrar(apps, schema_editor):
    EquiposServicios = apps.get_model('webcitt', 'EquiposServicios')
    for equipo in EquiposServicios.objects.filter(
            vida_util_referencia_anios=0).prefetch_related('categorias'):
        textos = [(equipo.nombre or '').lower(), (equipo.codigo or '').lower()]
        textos += [(categoria.nombre or '').lower() for categoria in equipo.categorias.all()]
        referencia = _referencia(textos)
        if referencia is None:
            continue
        equipo.vida_util_referencia_anios, equipo.vida_util_horas = referencia
        equipo.save(update_fields=['vida_util_referencia_anios', 'vida_util_horas'])


def retirar(apps, schema_editor):
    EquiposServicios = apps.get_model('webcitt', 'EquiposServicios')
    EquiposServicios.objects.update(vida_util_referencia_anios=0, vida_util_horas=0)


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0215_vida_util_de_referencia'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
