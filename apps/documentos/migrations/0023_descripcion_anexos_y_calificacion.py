"""Cada documento dice cómo se juzga y cada anexo lo que contiene y la meta que respalda.

Solo el informe semestral se califica, con el cumplimiento de las metas de la planificación; los demás documentos
son de cumplimiento obligatorio. Se reemplazan únicamente las descripciones de anexo vacías o las que el catálogo
tuvo antes; una descripción que la institución editó aparte se conserva. A los documentos principales, y a los anexos
cuyo texto ya describía su contenido, se les agrega una sola vez la frase que dice cómo se juzgan o qué meta respaldan.
"""
from django.db import migrations

# Frases que se agregan al final, una sola vez.
FRASES = {
    'RESOLUCION-CREACION': ('Cumplimiento obligatorio: la Dirección la aprueba una vez por versión; no se '
                            'califica.'),
    'PROTOCOLO-BIOSEGURIDAD': ('Cumplimiento obligatorio: se aprueba una vez y se conserva mientras siga vigente; '
                               'no se califica.'),
    'PLAN-COMPRAS-ANUAL': ('Cumplimiento obligatorio: la Dirección confirma su conformidad documental; no se '
                           'califica ni compromete fondos.'),
    'PLANIFICACION': ('Cumplimiento obligatorio: la Dirección confirma su conformidad; no se califica. '
                      'Sus metas son las que mide el informe semestral.'),
    'INFORME-SEMESTRAL': ('Es el único documento que se califica: su nota es el cumplimiento de las metas de '
                          'la planificación, medido con los registros y las evidencias del período, y no se '
                          'obtiene por haberlo entregado. Una entrega tardía descuenta los puntos que fija la '
                          'política de calidad.'),
    'PRESTAMOS-EQUIPOS': ('Respalda la meta opcional de préstamos de equipos: cuenta en la nota solo si la '
                          'planificación la incluyó.'),
    'PP-PRODUCCION': 'Respalda la meta de lotes o procesos de producción ejecutados.',
    'PP-CALIDAD': 'Respalda la meta de control de calidad de los lotes finalizados.',
    'CE-ENSAYOS': 'Respalda la meta de ensayos y parcelas con seguimiento.',
    'OBS-DATOS': 'Respalda la meta de actualización de series y fuentes del observatorio.',
    'OBS-BOLETINES': 'Respalda la meta de boletines, informes o bases de datos publicados.',
    'OBS-EVENTOS': 'Respalda la meta de eventos de socialización de resultados.',
}

# Descripción completa de cada anexo: qué trae y qué meta respalda.
ANEXOS = {
    'INDICADORES-PLAN': ('Programación consolidada del semestre: asignatura, fecha, escenario y responsable '
                         'de cada práctica, con su FT02 y su guía vinculados. Respalda la planificación; no '
                         'tiene meta propia (las prácticas aprobadas se miden en el FT02).'),
    'PLAN-MANTENIMIENTO': ('Equipos e infraestructura, criticidad, intervenciones, frecuencia, responsables y '
                           'calendario del año; viaja con la planificación del período A. Respalda la meta de '
                           'mantenimiento, que se mide en el informe semestral: 80 % de lo programado en '
                           'equipos críticos.'),
    'REGISTRO-USO': ('Sesiones registradas en la plataforma durante el período, agrupadas por propósito, '
                     'con fecha, horario, solicitante y estado. Respalda la meta de registrar todas las '
                     'sesiones de uso; el uso efectivo frente a la capacidad se detalla en los '
                     'indicadores del informe.'),
    'PRACTICAS-FT02': ('Matriz FT02 del período: cada práctica planificada con asignatura, fecha, '
                       'escenario, docente, responsable y guía, y la comprobación de su aprobación y su '
                       'respaldo. Respalda la meta de prácticas planificadas.'),
    'PRACTICAS-FT03': ('Registro FT03 del período: ejecución de cada práctica con asistencia, bitácora, '
                       'resultados y evidencias, y la comprobación de su respaldo. Respalda la meta de '
                       'prácticas ejecutadas.'),
    'GUIAS': ('Guías de práctica vigentes usadas en el período: código, versión, aprobación y '
              'vínculo con la asignatura y el syllabus. Respalda la meta de guías.'),
    'INDUCCION-SEGURIDAD': ('Requisitos de acceso, inducciones y habilitaciones de usuarios nuevos, '
                            'inspecciones de seguridad del período, incidentes y estado del protocolo vigente. '
                            'Respalda las metas de inducción de seguridad y de inspecciones.'),
    'DESECHOS': ('Desechos peligrosos y especiales del período: tipo, origen, cantidad, '
                 'almacenamiento, responsable y, cuando se entregan, gestor autorizado y manifiesto. '
                 'Respalda la meta de gestión de desechos.'),
    'EQUIPAMIENTO': ('Disponibilidad y funcionalidad del equipamiento en el período: estado al corte, '
                     'días fuera de servicio, verificaciones funcionales e incidencias. El inventario '
                     'completo va en el anexo de recursos. Respalda la meta opcional de disponibilidad '
                     'del equipamiento: cuenta en la nota solo si la planificación la incluyó.'),
    'INSUMOS-CORTE': ('Movimientos de reactivos e insumos del período (entradas, consumos y ajustes) y '
                      'existencias y lotes vigentes con sus vencimientos; complementa el inventario '
                      'integral. Respalda la meta opcional de movimientos de insumos: cuenta en la nota '
                      'solo si la planificación la incluyó.'),
    'INVENTARIO-CORTE': ('Inventario integral de la unidad al generarlo: equipos, software, espacios y, '
                         'donde aplica, insumos, con custodio, ubicación y condición. Respalda la meta de '
                         'revisión física del inventario, que se acredita con el acta verificada.'),
    'INVESTIGACION': ('Productos de investigación aplicada y desarrollo tecnológico obtenidos en el '
                      'período, con su proyecto, responsable y respaldo verificable; el uso de la unidad '
                      'para investigación y titulación se muestra aparte. Respalda la meta de resultados '
                      'de investigación.'),
    'TRANSFERENCIA': ('Entregables de transferencia de conocimiento y servicios especializados, con su '
                      'destinatario y su aceptación documentada; las solicitudes de servicio y las '
                      'reservas se muestran aparte. Respalda las metas de transferencia y de servicios.'),
    'ACCIONES-MEJORA': ('Acciones de mejora consolidadas desde los informes: hallazgo, acción, responsable, '
                        'plazo, estado y evidencia de cierre; su vista previa es el mismo documento que se '
                        'archiva. Respalda la meta opcional de seguimiento de acciones de mejora: cuenta en '
                        'la nota solo si la planificación la incluyó.'),
}

# Textos anteriores de esos anexos; solo estos (o una descripción vacía) se reemplazan.
ANTERIORES = {
    'INDICADORES-PLAN': (
        'Fecha, escenario y responsable de cada práctica planificada en el período.',
        ('Un documento consolidado del semestre reúne fecha, escenario y responsable de las '
         'prácticas por asignatura. Respalda la planificación semestral; la cantidad de '
         'prácticas aprobadas se mide en FT02, sin otra meta ni puntos independientes por '
         'este anexo.'),
    ),
    'PLAN-MANTENIMIENTO': (
        ('Viaja con la planificación del período A; ejecución mínima del 80 % en equipos '
         'críticos.'),
        ('Respalda la planificación del período A con equipos, criticidad, intervenciones, '
         'responsables y calendario. Su ejecución se contrasta con las intervenciones '
         'exigibles y las metas aprobadas.'),
    ),
    'REGISTRO-USO': (
        ('Lo produce el sistema con las reservas registradas; el 100 % de las sesiones debe '
         'pasar por la plataforma.'),
    ),
    'GUIAS': (
        'Al menos una guía nueva o actualizada por semestre.',
        ('Guías vigentes utilizadas en las prácticas programadas, con aprobación y vínculo '
         'con el syllabus.'),
    ),
    'INSUMOS-CORTE': (
        'Lo que se consume en el período; el inventario de equipos corta una vez al año.',
        ('Existencias al corte, lotes aplicables, entradas y consumos del período; '
         'complementa el inventario integral de recursos.'),
    ),
    'INVENTARIO-CORTE': (
        'Un corte al año, con el informe del período B: altas, bajas y fuera de servicio.',
    ),
    'INVESTIGACION': (
        ('Uso de la unidad para investigación, desarrollo y titulación, con su responsable y '
         'sus horas.'),
        ('Productos obtenidos, proyecto, responsable y respaldo verificable. El uso para '
         'investigación y titulación se muestra por separado.'),
    ),
    'TRANSFERENCIA': (
        'Servicios prestados, vinculación y capacitación, con su beneficiario.',
        ('Entregable, destinatario y aceptación documentada. Las solicitudes de servicio y '
         'reservas se muestran por separado.'),
    ),
    'ACCIONES-MEJORA': (
        ('Se consolida desde las acciones registradas en los informes semestrales: hallazgo, '
         'acción, responsable, plazo y estado.'),
    ),
}


def actualizar(apps, schema_editor):
    modelo = apps.get_model('documentos', 'DocumentoExigido')
    alias = schema_editor.connection.alias
    for documento in modelo.objects.using(alias).filter(codigo__in=[*FRASES, *ANEXOS]):
        actual = (documento.descripcion or '').strip()
        if documento.codigo in FRASES:
            frase = FRASES[documento.codigo].strip()
            if frase in actual:
                continue
            nueva = f'{actual} {frase}'.strip()
        elif actual == '' or actual in ANTERIORES.get(documento.codigo, ()):
            nueva = ANEXOS[documento.codigo]
        else:
            continue
        documento.descripcion = nueva
        documento.save(update_fields=['descripcion'])


class Migration(migrations.Migration):
    dependencies = [('documentos', '0022_marcopresupuestonecesidades_and_more')]
    # No se deshace: los textos anteriores eran incompletos o contradecían lo que el anexo contiene.
    operations = [migrations.RunPython(actualizar, migrations.RunPython.noop)]
