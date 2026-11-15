"""Expediente depurado: cada anexo aporta a una meta o es el único registro de lo que presenta.

- Se retiran cuatro anexos que repetían a otros o no respaldaban ninguna meta: el plan de prácticas por
  asignatura (INDICADORES-PLAN) y el plan de mantenimiento (PLAN-MANTENIMIENTO), que acompañaban a la
  planificación, y los préstamos (PRESTAMOS-EQUIPOS) y los insumos al corte (INSUMOS-CORTE), que acompañaban
  al informe. Quedan inactivos: sus filas del expediente, sus archivos y su historial se conservan; el
  Centro de reportes los sigue ofreciendo como consultas de gestión.
- EQUIPAMIENTO pasa a ser «Mantenimiento, disponibilidad y funcionalidad del equipamiento» y respalda la
  meta de mantenimiento (80 % de lo programado en equipos críticos) en los dos períodos.
- INVENTARIO-CORTE reúne los movimientos de insumos del período. Su periodicidad sigue anual en el catálogo:
  el perfil la vuelve semestral en todas las unidades menos los observatorios.
- Se corrigen las descripciones que prometían una «meta opcional que cuenta en la nota»: esas metas son
  registro del período y nunca cuentan.

Solo se reemplazan nombres y descripciones vacíos o idénticos a un texto anterior del catálogo distribuido;
de un texto editado por la institución solo se quita la frase falsa. Se puede aplicar más de una vez.
"""
from django.db import migrations

RETIRADOS = ('INDICADORES-PLAN', 'PLAN-MANTENIMIENTO', 'PRESTAMOS-EQUIPOS', 'INSUMOS-CORTE')

NOTAS_RETIRO = {
    'INDICADORES-PLAN': ('Retirado del expediente: repetía columnas del FT02 y no tenía meta. La planificación '
                         'trae la carga programada por asignatura y el Centro de reportes la conserva como '
                         'consulta. Las entregas anteriores se conservan.'),
    'PLAN-MANTENIMIENTO': ('Retirado del expediente: repetía los mantenimientos previstos de la planificación. '
                           'La ejecución del período y la meta de mantenimiento van en el anexo «Mantenimiento, '
                           'disponibilidad y funcionalidad del equipamiento». Las entregas anteriores se conservan.'),
    'PRESTAMOS-EQUIPOS': ('Retirado del expediente: los préstamos no tienen meta y se consultan en el Centro de '
                          'reportes. Las entregas anteriores se conservan.'),
    'INSUMOS-CORTE': ('Retirado del expediente: repetía las existencias y los lotes del inventario; sus '
                      'movimientos van en el anexo de inventario. Las entregas anteriores se conservan.'),
}

# Las metas de estos anexos son registro del período (ANEXOS_AUTOMATICOS): nunca cuentan en la nota.
FRASES_FALSAS = (
    'Respalda la meta opcional de préstamos de equipos: cuenta en la nota solo si la planificación la incluyó.',
    ('Respalda la meta opcional de disponibilidad del equipamiento: cuenta en la nota solo si la '
     'planificación la incluyó.'),
    'Respalda la meta opcional de movimientos de insumos: cuenta en la nota solo si la planificación la incluyó.',
    ('Respalda la meta opcional de seguimiento de acciones de mejora: cuenta en la nota solo si la '
     'planificación la incluyó.'),
)

NOMBRES = {
    'EQUIPAMIENTO': ('Equipamiento: disponibilidad y funcionalidad del período',
                     'Mantenimiento, disponibilidad y funcionalidad del equipamiento'),
    'INVENTARIO-CORTE': ('Inventario anual de equipos, software y espacios',
                         'Inventario de equipos, software, espacios e insumos al corte'),
}

DESCRIPCIONES = {
    'EQUIPAMIENTO': ('Mantenimientos del período, programados y ejecutados, con la medición del programa crítico '
                     'anual de equipos e infraestructura (80 % de lo programado en equipos críticos), y la '
                     'disponibilidad y funcionalidad de cada equipo: estado, días fuera de servicio, pruebas '
                     'funcionales e incidencias. No repite el inventario, que va en su propio anexo. Respalda la '
                     'meta de mantenimiento; la disponibilidad es registro del período, sin meta propia.'),
    'INVENTARIO-CORTE': ('Inventario integral de la unidad al corte: equipos, software y espacios con custodio, '
                         'ubicación y condición, el acta de revisión física y, donde hay insumos, sus '
                         'existencias, lotes y vencimientos y los movimientos del período (entradas, consumos y '
                         'ajustes). Se presenta cada semestre; en los observatorios, una vez al año con el informe '
                         'B. Respalda la meta de revisión física del inventario, que se acredita con el acta '
                         'verificada; los movimientos de insumos son registro del período, sin meta propia.'),
    'ACCIONES-MEJORA': ('Acciones de mejora consolidadas desde los informes: hallazgo, acción, responsable, plazo, '
                        'estado y evidencia de cierre; su vista previa es el mismo documento que se archiva. Es '
                        'registro del período: el seguimiento de las acciones no tiene meta propia ni cuenta en '
                        'la nota.'),
}

# Textos del catálogo distribuido que se reemplazan (documentos.0023 y anteriores).
ANTERIORES = {
    'EQUIPAMIENTO': (
        ('Disponibilidad y funcionalidad del equipamiento en el período: estado al corte, días fuera de '
         'servicio, verificaciones funcionales e incidencias. El inventario completo va en el anexo de '
         'recursos. Respalda la meta opcional de disponibilidad del equipamiento: cuenta en la nota solo si '
         'la planificación la incluyó.'),
    ),
    'INVENTARIO-CORTE': (
        ('Inventario integral de la unidad al generarlo: equipos, software, espacios y, donde aplica, insumos, '
         'con custodio, ubicación y condición. Respalda la meta de revisión física del inventario, que se '
         'acredita con el acta verificada.'),
        'Un corte al año, con el informe del período B: altas, bajas y fuera de servicio.',
        'Dos cortes al año con altas, bajas y fuera de servicio.',
    ),
    'ACCIONES-MEJORA': (
        ('Acciones de mejora consolidadas desde los informes: hallazgo, acción, responsable, plazo, estado y '
         'evidencia de cierre; su vista previa es el mismo documento que se archiva. Respalda la meta opcional '
         'de seguimiento de acciones de mejora: cuenta en la nota solo si la planificación la incluyó.'),
        ('Se consolida desde las acciones registradas en los informes semestrales: hallazgo, acción, '
         'responsable, plazo y estado.'),
        'Hallazgo, acción, responsable, plazo, estado y evidencia.',
    ),
    # Textos distribuidos de los anexos retirados, ya sin la frase falsa: se sustituyen por su nota de retiro.
    'INDICADORES-PLAN': (
        ('Programación consolidada del semestre: asignatura, fecha, escenario y responsable de cada práctica, '
         'con su FT02 y su guía vinculados. Respalda la planificación; no tiene meta propia (las prácticas '
         'aprobadas se miden en el FT02).'),
        'Fecha, escenario y responsable de cada práctica planificada en el período.',
        ('Un documento consolidado del semestre reúne fecha, escenario y responsable de las prácticas por '
         'asignatura. Respalda la planificación semestral; la cantidad de prácticas aprobadas se mide en FT02, '
         'sin otra meta ni puntos independientes por este anexo.'),
    ),
    'PLAN-MANTENIMIENTO': (
        ('Equipos e infraestructura, criticidad, intervenciones, frecuencia, responsables y calendario del '
         'año; viaja con la planificación del período A. Respalda la meta de mantenimiento, que se mide en el '
         'informe semestral: 80 % de lo programado en equipos críticos.'),
        'Viaja con la planificación del período A; ejecución mínima del 80 % en equipos críticos.',
        ('Respalda la planificación del período A con equipos, criticidad, intervenciones, responsables y '
         'calendario. Su ejecución se contrasta con las intervenciones exigibles y las metas aprobadas.'),
    ),
    'PRESTAMOS-EQUIPOS': (
        ('Quién retira, cuándo, para qué actividad y cuándo devuelve, con el estado del equipo. Sale de los '
         'préstamos registrados en la consola; el externo además exige su acta.'),
        'Quién retira, cuándo, para qué actividad y cuándo devuelve, con el estado del equipo.',
    ),
    'INSUMOS-CORTE': (
        ('Movimientos de reactivos e insumos del período (entradas, consumos y ajustes) y existencias y lotes '
         'vigentes con sus vencimientos; complementa el inventario integral.'),
        'Lo que se consume en el período; el inventario de equipos corta una vez al año.',
        ('Existencias al corte, lotes aplicables, entradas y consumos del período; complementa el inventario '
         'integral de recursos.'),
        ('El inventario de equipos corta aparte; este cubre lo que se consume. Solo cuando la unidad lleva '
         'insumos.'),
    ),
}


def _sin_frases_falsas(texto):
    for frase in FRASES_FALSAS:
        texto = texto.replace(frase, '')
    return ' '.join(texto.split())


def depurar(apps, schema_editor):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    codigos = (*RETIRADOS, *NOMBRES, *DESCRIPCIONES)
    for exigido in modelo.objects.using(alias).filter(codigo__in=codigos):
        cambios = {}
        actual = ' '.join((exigido.descripcion or '').split())
        if exigido.codigo in RETIRADOS:
            if exigido.activo:
                cambios['activo'] = False
            nota = NOTAS_RETIRO[exigido.codigo]
            nueva = _sin_frases_falsas(actual)
            if nueva in ANTERIORES[exigido.codigo]:
                # Un texto distribuido describía un anexo que ya no se pide: queda solo la nota de retiro.
                nueva = nota
            elif nota not in nueva:
                nueva = f'{nueva} {nota}'.strip()
        elif actual == '' or _sin_frases_falsas(actual) in {
                _sin_frases_falsas(texto) for texto in ANTERIORES.get(exigido.codigo, ())}:
            nueva = DESCRIPCIONES[exigido.codigo]
        else:
            # Texto editado por la institución: se conserva, sin la promesa de una meta que no cuenta.
            nueva = _sin_frases_falsas(actual)
        if nueva != (exigido.descripcion or ''):
            cambios['descripcion'] = nueva
        anterior, nombre = NOMBRES.get(exigido.codigo, (None, None))
        if anterior is not None and exigido.nombre == anterior:
            cambios['nombre'] = nombre
        if cambios:
            for campo, valor in cambios.items():
                setattr(exigido, campo, valor)
            exigido.save(update_fields=list(cambios))


def restaurar(apps, schema_editor):
    """Reactiva lo retirado y devuelve los nombres y textos que esta migración escribió.

    No vuelve a escribir la frase de la «meta opcional que cuenta en la nota»: era falsa. Las descripciones
    que la institución editó después de aplicar esta migración se conservan.
    """
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    codigos = (*RETIRADOS, *NOMBRES, *DESCRIPCIONES)
    for exigido in modelo.objects.using(alias).filter(codigo__in=codigos):
        cambios = {}
        descripcion = exigido.descripcion or ''
        if exigido.codigo in RETIRADOS:
            if not exigido.activo:
                cambios['activo'] = True
            nota = NOTAS_RETIRO[exigido.codigo]
            if descripcion == nota:
                cambios['descripcion'] = ANTERIORES[exigido.codigo][0]
            elif nota in descripcion:
                cambios['descripcion'] = ' '.join(descripcion.replace(nota, '').split())
        elif descripcion == DESCRIPCIONES[exigido.codigo] and ANTERIORES.get(exigido.codigo):
            cambios['descripcion'] = _sin_frases_falsas(ANTERIORES[exigido.codigo][0])
        anterior, nombre = NOMBRES.get(exigido.codigo, (None, None))
        if nombre is not None and exigido.nombre == nombre:
            cambios['nombre'] = anterior
        if cambios:
            for campo, valor in cambios.items():
                setattr(exigido, campo, valor)
            exigido.save(update_fields=list(cambios))


class Migration(migrations.Migration):
    dependencies = [('documentos', '0023_descripcion_anexos_y_calificacion')]
    operations = [migrations.RunPython(depurar, restaurar)]
