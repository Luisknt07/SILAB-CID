"""Anexos del informe: cinco, cada uno respalda un grupo de metas con las cifras del informe.

- PRACTICAS-FT02 pasa a «Prácticas académicas: planificación, ejecución y guías» y absorbe la ejecución
  (PRACTICAS-FT03) y las guías (GUIAS).
- INDUCCION-SEGURIDAD pasa a «Seguridad y desechos» y absorbe los desechos (DESECHOS).
- EQUIPAMIENTO pasa a «Equipos e inventario» y absorbe el inventario al corte (INVENTARIO-CORTE): el acta
  de revisión física y un resumen; la lista completa queda como consulta del Centro de reportes.
- INVESTIGACION pasa a «Investigación y vinculación» y absorbe la transferencia (TRANSFERENCIA); solo se
  presenta cuando la planificación del período compromete alguna de esas metas.
- REGISTRO-USO pasa a «Uso de la unidad: sesiones, horas y usuarios».
- ACCIONES-MEJORA se retira: las acciones de mejora van en la sección 8 del informe.

Los seis retirados quedan inactivos: sus filas del expediente, sus archivos y su historial se conservan.
Solo se reemplazan nombres y descripciones idénticos al catálogo distribuido; lo editado por la
institución se conserva. Se puede aplicar más de una vez y se puede revertir.
"""
from django.db import migrations

RETIRADOS = ('PRACTICAS-FT03', 'GUIAS', 'DESECHOS', 'INVENTARIO-CORTE', 'TRANSFERENCIA', 'ACCIONES-MEJORA')
NOTA_RETIRO = ('Retirado del expediente (documentos.0025): su contenido va en uno de los cinco anexos del '
               'informe semestral o en el propio informe. Las entregas anteriores se conservan.')

NOMBRES = {
    'PRACTICAS-FT02': ('FT02 · Planificación de cada práctica',
        'Prácticas académicas: planificación, ejecución y guías'),
    'REGISTRO-USO': ('Registro de uso del período: sesiones, horas y usuarios por tipo y finalidad',
        'Uso de la unidad: sesiones, horas y usuarios'),
    'INDUCCION-SEGURIDAD': ('Registro de inducciones y controles de seguridad',
        'Seguridad y desechos: inducciones, inspecciones y desechos'),
    'EQUIPAMIENTO': ('Mantenimiento, disponibilidad y funcionalidad del equipamiento',
        'Equipos e inventario: revisión física, mantenimiento y existencias'),
    'INVESTIGACION': ('Resultados de investigación aplicada y desarrollo tecnológico',
        'Investigación y vinculación: resultados, transferencia y servicios'),
}

DESCRIPCIONES = {
    'PRACTICAS-FT02': (('Matriz FT02 del período: cada práctica planificada con asignatura, fecha, escenario, '
         'docente, responsable y guía, y la comprobación de su aprobación y su respaldo. Respalda la '
         'meta de prácticas planificadas.'),
        ('Prácticas planificadas y aprobadas, prácticas ejecutadas con asistencia y evidencias, y '
         'guías de práctica vigentes, con lo que falta a cada registro para contar. Respalda las metas '
         'de prácticas planificadas, prácticas ejecutadas y guías.')),
    'REGISTRO-USO': (('Sesiones registradas en la plataforma durante el período, agrupadas por propósito, con '
         'fecha, horario, solicitante y estado. Respalda la meta de registrar todas las sesiones de '
         'uso; el uso efectivo frente a la capacidad se detalla en los indicadores del informe.'),
        ('Sesiones registradas y atendidas del período, horas de uso efectivo y usuarios, por '
         'propósito, con el detalle de las sesiones atendidas. Respalda las metas de registro de '
         'sesiones y de uso efectivo.')),
    'INDUCCION-SEGURIDAD': (('Requisitos de acceso, inducciones y habilitaciones de usuarios nuevos, inspecciones de '
         'seguridad del período, incidentes y estado del protocolo vigente. Respalda las metas de '
         'inducción de seguridad y de inspecciones.'),
        ('Inspecciones mensuales, inducciones y habilitaciones de usuarios nuevos, ingresos a la '
         'unidad y desechos peligrosos y especiales generados y entregados. Respalda las metas de '
         'inducción, inspecciones y gestión de desechos.')),
    'EQUIPAMIENTO': (('Mantenimientos del período, programados y ejecutados, con la medición del programa crítico '
         'anual de equipos e infraestructura (80 % de lo programado en equipos críticos), y la '
         'disponibilidad y funcionalidad de cada equipo: estado, días fuera de servicio, pruebas '
         'funcionales e incidencias. No repite el inventario, que va en su propio anexo. Respalda la '
         'meta de mantenimiento; la disponibilidad es registro del período, sin meta propia.'),
        ('Acta de revisión física del inventario, datos pendientes de los equipos, mantenimientos del '
         'período frente al programa crítico (80 %), equipos fuera de servicio e insumos bajo su '
         'mínimo. Respalda las metas de revisión del inventario y de mantenimiento.')),
    'INVESTIGACION': (('Productos de investigación aplicada y desarrollo tecnológico obtenidos en el período, con su '
         'proyecto, responsable y respaldo verificable; el uso de la unidad para investigación y '
         'titulación se muestra aparte. Respalda la meta de resultados de investigación.'),
        ('Solo cuando la planificación compromete estas metas: productos de investigación, '
         'transferencias y servicios entregados y aceptados, con su respaldo. Respalda las metas de '
         'investigación, transferencia y servicios.')),
}

DESCRIPCIONES_RETIRADOS = {
    'PRACTICAS-FT03': ('Registro FT03 del período: ejecución de cada práctica con asistencia, bitácora, resultados y '
     'evidencias, y la comprobación de su respaldo. Respalda la meta de prácticas ejecutadas.'),
    'GUIAS': ('Guías de práctica vigentes usadas en el período: código, versión, aprobación y vínculo con la '
     'asignatura y el syllabus. Respalda la meta de guías.'),
    'DESECHOS': ('Desechos peligrosos y especiales del período: tipo, origen, cantidad, almacenamiento, '
     'responsable y, cuando se entregan, gestor autorizado y manifiesto. Respalda la meta de gestión '
     'de desechos.'),
    'INVENTARIO-CORTE': ('Inventario integral de la unidad al corte: equipos, software y espacios con custodio, ubicación '
     'y condición, el acta de revisión física y, donde hay insumos, sus existencias, lotes y '
     'vencimientos y los movimientos del período (entradas, consumos y ajustes). Se presenta cada '
     'semestre; en los observatorios, una vez al año con el informe B. Respalda la meta de revisión '
     'física del inventario, que se acredita con el acta verificada; los movimientos de insumos son '
     'registro del período, sin meta propia.'),
    'TRANSFERENCIA': ('Entregables de transferencia de conocimiento y servicios especializados, con su destinatario y '
     'su aceptación documentada; las solicitudes de servicio y las reservas se muestran aparte. '
     'Respalda las metas de transferencia y de servicios.'),
    'ACCIONES-MEJORA': ('Acciones de mejora consolidadas desde los informes: hallazgo, acción, responsable, plazo, estado '
     'y evidencia de cierre; su vista previa es el mismo documento que se archiva. Es registro del '
     'período: el seguimiento de las acciones no tiene meta propia ni cuenta en la nota.'),
}


def _iguales(a, b):
    return ' '.join((a or '').split()) == ' '.join((b or '').split())


def fusionar(apps, schema_editor):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    for exigido in modelo.objects.using(alias).filter(codigo__in=(*RETIRADOS, *NOMBRES)):
        cambios = {}
        if exigido.codigo in RETIRADOS:
            if exigido.activo:
                cambios['activo'] = False
            descripcion = exigido.descripcion or ''
            if _iguales(descripcion, DESCRIPCIONES_RETIRADOS[exigido.codigo]):
                cambios['descripcion'] = NOTA_RETIRO
            elif NOTA_RETIRO not in descripcion:
                cambios['descripcion'] = f'{descripcion} {NOTA_RETIRO}'.strip()
        else:
            anterior, nuevo = NOMBRES[exigido.codigo]
            if exigido.nombre == anterior:
                cambios['nombre'] = nuevo
            anterior, nuevo = DESCRIPCIONES[exigido.codigo]
            if not (exigido.descripcion or '').strip() or _iguales(exigido.descripcion, anterior):
                cambios['descripcion'] = nuevo
        if cambios:
            for campo, valor in cambios.items():
                setattr(exigido, campo, valor)
            exigido.save(update_fields=list(cambios))


def separar(apps, schema_editor):
    """Reactiva los seis anexos y devuelve los nombres y textos que esta migración escribió."""
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    for exigido in modelo.objects.using(alias).filter(codigo__in=(*RETIRADOS, *NOMBRES)):
        cambios = {}
        descripcion = exigido.descripcion or ''
        if exigido.codigo in RETIRADOS:
            if not exigido.activo:
                cambios['activo'] = True
            if descripcion == NOTA_RETIRO:
                cambios['descripcion'] = DESCRIPCIONES_RETIRADOS[exigido.codigo]
            elif NOTA_RETIRO in descripcion:
                cambios['descripcion'] = ' '.join(descripcion.replace(NOTA_RETIRO, '').split())
        else:
            anterior, nuevo = NOMBRES[exigido.codigo]
            if exigido.nombre == nuevo:
                cambios['nombre'] = anterior
            anterior, nuevo = DESCRIPCIONES[exigido.codigo]
            if descripcion == nuevo:
                cambios['descripcion'] = anterior
        if cambios:
            for campo, valor in cambios.items():
                setattr(exigido, campo, valor)
            exigido.save(update_fields=list(cambios))


class Migration(migrations.Migration):
    dependencies = [('documentos', '0024_expediente_depurado')]
    operations = [migrations.RunPython(fusionar, separar)]
