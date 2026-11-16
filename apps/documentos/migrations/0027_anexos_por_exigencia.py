"""Anexos del informe: uno por cada documento que pide la universidad.

Deshace la fusión de documentos.0025 donde juntaba exigencias distintas y nombra cada anexo con la
redacción de la universidad. La estructura está en docs/estructura-anexos-por-tipo-de-unidad.md.

- Vuelven como anexos propios, con nombre nuevo: guías (GUIAS), evidencias de prácticas (PRACTICAS-FT03),
  desechos (DESECHOS), inventario (INVENTARIO-CORTE) y transferencia (TRANSFERENCIA).
- Cambian de nombre y de alcance: uso, mantenimiento y equipamiento, planificación de las prácticas,
  seguridad e investigación.
- Se crean dos: fichas técnicas (FICHAS-TECNICAS) y producción agropecuaria del centro experimental
  (CE-PRODUCCION).
- El orden numera los anexos: comunes, propios del tipo de unidad y, al final, los condicionales.

Solo se reemplazan nombres, descripciones y órdenes idénticos a los del catálogo distribuido; lo editado
por la institución se conserva. Se puede aplicar más de una vez y se puede revertir. Al revertir, un
anexo creado aquí que ya tenga documentos queda inactivo en lugar de borrarse.
"""
from django.db import migrations

NOTA_RETIRO = 'Retirado del expediente (documentos.0025): su contenido va en uno de los cinco anexos del informe semestral o en el propio informe. Las entregas anteriores se conservan.'
REACTIVADOS = ('PRACTICAS-FT03', 'GUIAS', 'DESECHOS', 'INVENTARIO-CORTE', 'TRANSFERENCIA')
# código: (nombre anterior, nombre nuevo)
NOMBRES = {'REGISTRO-USO': ('Uso de la unidad: sesiones, horas y usuarios', 'Registros de uso de la unidad'),
 'EQUIPAMIENTO': ('Equipos e inventario: revisión física, mantenimiento y existencias',
                  'Plan de mantenimiento de equipos e informe de equipamiento, disponibilidad y funcionalidad'),
 'INVENTARIO-CORTE': ('Inventario de equipos, software, espacios e insumos al corte',
                      'Inventario de equipamiento, reactivos e insumos'),
 'PRACTICAS-FT02': ('Prácticas académicas: planificación, ejecución y guías',
                    'Planificación semestral de las prácticas'),
 'GUIAS': ('Guías de prácticas: aprobación y vínculo con el syllabus', 'Guías de prácticas'),
 'PRACTICAS-FT03': ('FT03 · Registro de ejecución con asistencia, bitácora y evidencias',
                    'Registros de asistencia y evidencias de las prácticas'),
 'INDUCCION-SEGURIDAD': ('Seguridad y desechos: inducciones, inspecciones y desechos',
                         'Reportes de seguridad y condiciones de operación'),
 'DESECHOS': ('Registro de desechos peligrosos y especiales',
              'Registros de gestión de desechos peligrosos y especiales'),
 'INVESTIGACION': ('Investigación y vinculación: resultados, transferencia y servicios',
                   'Informe de resultados de investigación aplicada y desarrollo tecnológico'),
 'TRANSFERENCIA': ('Transferencia de conocimiento y servicios especializados a la sociedad',
                   'Informe de transferencia de conocimiento, tecnología y servicios especializados a la '
                   'sociedad'),
 'CE-ENSAYOS': ('Ensayos del centro experimental: parcelas y seguimiento', 'Ensayos y parcelas experimentales')}
# código: nombres del catálogo distribuido que se reconocen como no editados
NOMBRES_ANTERIORES = {'REGISTRO-USO': ['Registro de uso del período: sesiones, horas y usuarios por tipo y finalidad',
                  'Uso de la unidad: sesiones, horas y usuarios'],
 'EQUIPAMIENTO': ['Equipamiento: disponibilidad y funcionalidad del período',
                  'Equipos e inventario: revisión física, mantenimiento y existencias',
                  'Mantenimiento, disponibilidad y funcionalidad del equipamiento'],
 'INVENTARIO-CORTE': ['Inventario anual de equipos, software y espacios',
                      'Inventario de equipos, software, espacios e insumos al corte'],
 'PRACTICAS-FT02': ['FT02 · Planificación de cada práctica',
                    'Prácticas académicas: planificación, ejecución y guías'],
 'GUIAS': ['Guías de prácticas: aprobación y vínculo con el syllabus'],
 'PRACTICAS-FT03': ['FT03 · Registro de ejecución con asistencia, bitácora y evidencias'],
 'INDUCCION-SEGURIDAD': ['Registro de inducciones y controles de seguridad',
                         'Seguridad y condiciones de operación: protocolo, inducciones y controles',
                         'Seguridad y desechos: inducciones, inspecciones y desechos'],
 'DESECHOS': ['Registro de desechos peligrosos y especiales'],
 'INVESTIGACION': ['Investigación y vinculación: resultados, transferencia y servicios',
                   'Resultados de investigación aplicada y desarrollo tecnológico'],
 'TRANSFERENCIA': ['Transferencia de conocimiento y servicios especializados a la sociedad'],
 'CE-ENSAYOS': ['Ensayos del centro experimental: parcelas y seguimiento',
                'Informe de ensayos y seguimiento de parcelas experimentales']}
# código: (orden anterior, orden nuevo)
ORDENES = {'EQUIPAMIENTO': (40, 20),
 'INVENTARIO-CORTE': (30, 30),
 'PRACTICAS-FT02': (20, 50),
 'GUIAS': (40, 60),
 'PRACTICAS-FT03': (30, 70),
 'INDUCCION-SEGURIDAD': (70, 80),
 'DESECHOS': (80, 110),
 'INVESTIGACION': (60, 120),
 'TRANSFERENCIA': (70, 130),
 'OBS-DATOS': (20, 90),
 'OBS-BOLETINES': (30, 92),
 'OBS-EVENTOS': (40, 94)}
# código: (descripción anterior, descripción nueva)
DESCRIPCIONES = {'REGISTRO-USO': ('Sesiones registradas y atendidas del período, horas de uso efectivo y usuarios, por '
                  'propósito, con el detalle de las sesiones atendidas. Respalda las metas de registro de '
                  'sesiones y de uso efectivo.',
                  'Todas las sesiones del período con su horario previsto y real, espacio o recurso, '
                  'propósito, solicitante, participantes, cierre y horas efectivas; totales por propósito y '
                  'por mes, y visitas. Respalda las metas de registro de sesiones y de uso efectivo.'),
 'EQUIPAMIENTO': ('Acta de revisión física del inventario, datos pendientes de los equipos, mantenimientos del '
                  'período frente al programa crítico (80 %), equipos fuera de servicio e insumos bajo su '
                  'mínimo. Respalda las metas de revisión del inventario y de mantenimiento.',
                  'Plan de mantenimiento vigente por equipo, mantenimientos del período con su informe, '
                  'cumplimiento del plan en los equipos críticos, fallas y días fuera de servicio, pruebas '
                  'funcionales, estado de los equipos al corte y mantenimiento de la infraestructura. Respalda '
                  'la meta de mantenimiento.'),
 'INVENTARIO-CORTE': ('Retirado del expediente (documentos.0025): su contenido va en uno de los cinco anexos '
                      'del informe semestral o en el propio informe. Las entregas anteriores se conservan.',
                      'Acta de revisión física, equipos con su identificación, custodia y estado, bajas y '
                      'traspasos, reactivos por lote, insumos y materiales, y movimientos del período. Se '
                      'presenta cada semestre; en los observatorios, una vez al año con el informe B. Respalda '
                      'la meta de revisión física del inventario.'),
 'PRACTICAS-FT02': ('Prácticas planificadas y aprobadas, prácticas ejecutadas con asistencia y evidencias, y '
                    'guías de práctica vigentes, con lo que falta a cada registro para contar. Respalda las '
                    'metas de prácticas planificadas, prácticas ejecutadas y guías.',
                    'Todas las prácticas planificadas, por asignatura: unidad y tema del syllabus, fecha, '
                    'escenario, responsable técnico, estudiantes previstos, guía y estado de su revisión; '
                    'sesiones programadas sin planificación y resumen por asignatura. Respalda la meta de '
                    'prácticas planificadas.'),
 'GUIAS': ('Retirado del expediente (documentos.0025): su contenido va en uno de los cinco anexos del informe '
           'semestral o en el propio informe. Las entregas anteriores se conservan.',
           'Guías vigentes con su versión, vínculo con la asignatura y el syllabus, aprobación y enlace al '
           'documento; comprobación de su contenido mínimo y versiones sustituidas en el período. Respalda la '
           'meta de guías.'),
 'PRACTICAS-FT03': ('Retirado del expediente (documentos.0025): su contenido va en uno de los cinco anexos del '
                    'informe semestral o en el propio informe. Las entregas anteriores se conservan.',
                    'Ejecución de cada práctica, asistencia nominal e índice de evidencias por tipo '
                    '(asistencia firmada, bitácora, fotografías identificadas, capturas de simulador, informes '
                    'de estudiantes y productos desarrollados), con enlace a cada archivo. Respalda la meta de '
                    'prácticas ejecutadas.'),
 'INDUCCION-SEGURIDAD': ('Inspecciones mensuales, inducciones y habilitaciones de usuarios nuevos, ingresos a '
                         'la unidad y desechos peligrosos y especiales generados y entregados. Respalda las '
                         'metas de inducción, inspecciones y gestión de desechos.',
                         'Requisitos de acceso, inducciones y habilitaciones, inspecciones de condiciones con '
                         'sus hallazgos y acciones correctivas, cobertura mensual, control de ingresos e '
                         'incidentes de seguridad. Respalda las metas de inducción y de inspecciones.'),
 'DESECHOS': ('Retirado del expediente (documentos.0025): su contenido va en uno de los cinco anexos del '
              'informe semestral o en el propio informe. Las entregas anteriores se conservan.',
              'Generación y almacenamiento de cada desecho, entregas al gestor autorizado con su manifiesto y '
              'lo almacenado al corte. Se presenta cuando la unidad genera desechos o guarda reactivos, '
              'agroquímicos o medicamentos veterinarios. Respalda la meta de gestión de desechos.'),
 'INVESTIGACION': ('Solo cuando la planificación compromete estas metas: productos de investigación, '
                   'transferencias y servicios entregados y aceptados, con su respaldo. Respalda las metas de '
                   'investigación, transferencia y servicios.',
                   'Resultados de investigación con su proyecto, producto, responsable y respaldo verificable, '
                   'y uso de la unidad para investigación. Se presenta cuando la planificación compromete la '
                   'meta. Respalda la meta de resultados de investigación.'),
 'TRANSFERENCIA': ('Retirado del expediente (documentos.0025): su contenido va en uno de los cinco anexos del '
                   'informe semestral o en el propio informe. Las entregas anteriores se conservan.',
                   'Transferencias con su destinatario y aceptación documentada, y servicios especializados '
                   'atendidos. Se presenta cuando la planificación los compromete o hubo servicios atendidos. '
                   'Respalda las metas de transferencia y de servicios.'),
 'CE-ENSAYOS': ('Objetivo, escenario, fechas, manejo, mediciones y resultados respaldados de los ensayos. '
                'Respalda la meta de ensayos y parcelas con seguimiento.',
                'Ensayos con su objetivo, diseño, parcela, fechas y responsable; seguimiento y mediciones, y '
                'resultados respaldados. Respalda la meta de ensayos y parcelas con seguimiento.')}
# Anexos que no existían
NUEVOS = {'FICHAS-TECNICAS': {'nombre': 'Fichas técnicas de laboratorios, talleres, software, simuladores y espacios',
                     'carpeta': 'evaluacion',
                     'periodicidad': 'semestral',
                     'origen': 'sistema',
                     'requiere_firma': False,
                     'condicional': False,
                     'plazo_regla': 'cierre',
                     'plazo_dias': 15,
                     'fuente_reporte': 'fichas-tecnicas',
                     'orden': 40,
                     'descripcion': 'Ficha de la unidad (ubicación, responsable, horario y capacidad), '
                                    'espacios y talleres con su capacidad, mobiliario y equipos asociados, y '
                                    'software y simuladores con su versión, acceso y licencias. Es registro '
                                    'del período, sin meta propia.',
                     'tipos_unidad': []},
 'CE-PRODUCCION': {'nombre': 'Producción agropecuaria: ciclos, labores, sanidad y cosechas',
                   'carpeta': 'ejecucion',
                   'periodicidad': 'semestral',
                   'origen': 'sistema',
                   'requiere_firma': False,
                   'condicional': False,
                   'plazo_regla': 'cierre',
                   'plazo_dias': 15,
                   'fuente_reporte': 'produccion-agropecuaria',
                   'orden': 95,
                   'descripcion': 'Ciclos productivos que no son ensayos, con su meta y lo obtenido; labores, '
                                  'sanidad e insumos aplicados; producción obtenida y su destino, y animales '
                                  'al corte. Es registro del período, sin meta propia.',
                   'tipos_unidad': ['centro_experimental']}}


def _iguales(a, b):
    return ' '.join((a or '').split()) == ' '.join((b or '').split())


def separar_por_exigencia(apps, schema_editor):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    informe = modelo.objects.using(alias).filter(codigo='INFORME-SEMESTRAL').first()
    for exigido in modelo.objects.using(alias).filter(codigo__in=NOMBRES.keys() | ORDENES.keys() | DESCRIPCIONES.keys()):
        cambios, codigo = {}, exigido.codigo
        descripcion = exigido.descripcion or ''
        if codigo in REACTIVADOS and NOTA_RETIRO in descripcion:
            # Solo vuelve lo que retiró documentos.0025; lo que la institución desactivó sigue así.
            if not exigido.activo:
                cambios['activo'] = True
            cambios['descripcion'] = (DESCRIPCIONES[codigo][1] if _iguales(descripcion, NOTA_RETIRO)
                                      else ' '.join(descripcion.replace(NOTA_RETIRO, '').split()))
        elif codigo in DESCRIPCIONES and codigo not in REACTIVADOS:
            anterior, nueva = DESCRIPCIONES[codigo]
            if not descripcion.strip() or _iguales(descripcion, anterior):
                cambios['descripcion'] = nueva
        if codigo in NOMBRES and exigido.nombre in NOMBRES_ANTERIORES[codigo]:
            cambios['nombre'] = NOMBRES[codigo][1]
        if codigo in ORDENES and exigido.orden == ORDENES[codigo][0]:
            cambios['orden'] = ORDENES[codigo][1]
        if cambios:
            for campo, valor in cambios.items():
                setattr(exigido, campo, valor)
            exigido.save(update_fields=list(cambios))
    if informe is None:
        return
    for codigo, datos in NUEVOS.items():
        modelo.objects.using(alias).get_or_create(codigo=codigo, defaults=dict(datos, anexo_de=informe, activo=True))


def fusionar_de_nuevo(apps, schema_editor):
    """Devuelve el catálogo al estado de documentos.0026."""
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    expediente = apps.get_model('documentos', 'DocumentoExpediente')
    alias = schema_editor.connection.alias
    for exigido in modelo.objects.using(alias).filter(codigo__in=NOMBRES.keys() | ORDENES.keys() | DESCRIPCIONES.keys()):
        cambios, codigo = {}, exigido.codigo
        if codigo in DESCRIPCIONES and (exigido.descripcion or '') == DESCRIPCIONES[codigo][1]:
            cambios['descripcion'] = DESCRIPCIONES[codigo][0]
            if codigo in REACTIVADOS and exigido.activo:
                cambios['activo'] = False
        if codigo in NOMBRES and exigido.nombre == NOMBRES[codigo][1]:
            cambios['nombre'] = NOMBRES[codigo][0]
        if codigo in ORDENES and exigido.orden == ORDENES[codigo][1]:
            cambios['orden'] = ORDENES[codigo][0]
        if cambios:
            for campo, valor in cambios.items():
                setattr(exigido, campo, valor)
            exigido.save(update_fields=list(cambios))
    for exigido in modelo.objects.using(alias).filter(codigo__in=NUEVOS):
        if expediente.objects.using(alias).filter(exigido=exigido).exists():
            if exigido.activo:
                exigido.activo = False
                exigido.save(update_fields=['activo'])
        else:
            exigido.delete()


def inventario_con_el_periodo_del_informe(apps, schema_editor):
    """El inventario que todavía no se entregó toma el período del informe al que acompaña.

    Con la regla anual anterior, algunas filas del semestre B guardaron el año completo como período: su
    anexo repetiría los movimientos del semestre A. Solo se corrigen las pendientes y los borradores que
    nadie entregó ni validó; lo entregado conserva su período. El observatorio presenta su inventario una vez
    al año y no se toca.
    """
    expediente = apps.get_model('documentos', 'DocumentoExpediente')
    alias = schema_editor.connection.alias
    filas = (expediente.objects.using(alias)
             .filter(exigido__codigo='INVENTARIO-CORTE', corte__in=('A', 'B'), mes__isnull=True,
                     estado__in=('pendiente', 'generado'), entregado_en__isnull=True, validado_en__isnull=True)
             .exclude(unidad__dependencia='observatorios'))
    for fila in filas:
        informe = expediente.objects.using(alias).filter(
            unidad_id=fila.unidad_id, anio=fila.anio, corte=fila.corte, mes__isnull=True,
            exigido__codigo='INFORME-SEMESTRAL').first()
        if informe is None or not (informe.tramo_inicio and informe.tramo_fin):
            continue
        if (fila.tramo_inicio, fila.tramo_fin) != (informe.tramo_inicio, informe.tramo_fin):
            fila.tramo_inicio, fila.tramo_fin = informe.tramo_inicio, informe.tramo_fin
            fila.save(update_fields=['tramo_inicio', 'tramo_fin'])


class Migration(migrations.Migration):
    dependencies = [('documentos', '0026_anexos_propios_como_registro')]
    operations = [migrations.RunPython(separar_por_exigencia, fusionar_de_nuevo),
                  # No se revierte: un inventario semestral con el período del año era un error.
                  migrations.RunPython(inventario_con_el_periodo_del_informe, migrations.RunPython.noop)]
