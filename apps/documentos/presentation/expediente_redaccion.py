"""Editor guiado de la planificación y del informe semestral de una unidad.

Funciona como el de las guías de práctica: el documento se llena por
apartados, el sistema pone lo que ya sabe (la ficha de la unidad, sus
espacios, servicios, inventario y, en el informe, lo registrado en el período),
la unidad escribe lo que solo ella conoce, y al final el editor dice qué falta
y cuáles son los pasos para firmar y cargar el PDF.

Todo lo automático se lee al mostrar y al generar; en la base solo queda lo
que la unidad escribió (`DocumentoElaborado.contenido`).
"""

from itertools import zip_longest
from copy import deepcopy
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages

from apps.finanzas.presentation.presupuesto import bloque_de_sugerencias
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.laboratorios.operacion.models.fablab import FablabService, SolicitudFabricacion
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.reservas.models.seguridad import HabilitacionAcceso
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.workflows.reservas import ESTADOS_ATENCION_EFECTIVA
from apps.documentos.presentation.metas_plan import (
    ANEXOS_AUTOMATICOS, control_meta, meta_con_minimo, obligatoria_por_tipo,
)
from apps.documentos.presentation.perfil_laboratorios import referencia_interna
from apps.documentos.presentation.perfil_unidades import base_de, es_unidad_auditable
from apps.documentos.presentation.presupuesto_documental import (
    CATEGORIAS_INVERSION, PRIORIDADES, FUENTES_FINANCIAMIENTO, analizar_presupuesto,
)

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.documentos.presentation.expediente_sugerencias import POLITICA_POR_CAMPO as POLITICAS_RICAS, sugerencias_para
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.reservas.presentation.guia_html import bloques_de_html, esta_vacio, sanear, texto_a_html

MESES_CORTOS = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
NOMBRES_TIPO = {'planificacion': 'Planificación semestral', 'informe': 'Informe semestral de actividades',
                'compras': 'Plan anual de compras', 'protocolo': 'Protocolo de seguridad y condiciones de operación'}
CODIGOS_FORMATO = {'planificacion': 'AP-P-LAP-GO', 'informe': 'AP-P-LAP-GO · Informe',
                   'compras': 'AP-P-LAP-GO · Compras', 'protocolo': 'SLCID-UNIDAD-SEGURIDAD'}
ESTADOS_RESERVA_DESCARTADOS = ('cancelada', 'rechazada', 'vencida')


# -- definición de los apartados ---------------------------------------------

@dataclass(frozen=True)
class Campo:
    clave: str
    etiqueta: str
    tipo: str            # texto · rico · tabla · opcion · marcas · actividades · cumplimiento
    requerido: bool = False
    ayuda: str = ''
    columnas: tuple = ()  # tabla: (clave, etiqueta, tipo, opciones)
    opciones: tuple = ()
    ejemplo: str = ''


@dataclass(frozen=True)
class Seccion:
    codigo: str
    titulo: str
    descripcion: str
    campos: tuple
    automatico: str = ''   # qué bloque automático encabeza el apartado


SECTORES = (
    ('docencia', 'Docencia y formación de grado'), ('investigacion', 'Investigación y desarrollo'),
    ('vinculacion', 'Vinculación con la sociedad'), ('productivo', 'Sector productivo y empresarial'),
    ('publico', 'Sector público y gobiernos locales'), ('salud', 'Salud'),
    ('agro', 'Agropecuario y agroindustrial'), ('ambiente', 'Ambiente y recursos naturales'),
    ('tecnologia', 'Tecnología e innovación'), ('comunidad', 'Comunidad y territorio'),
)
ESTADOS_OPERATIVOS = (
    ('A', 'A · Operación completa: equipamiento, personal y espacios suficientes'),
    ('B', 'B · Operación parcial: funciona con limitaciones que se detallan'),
    ('C', 'C · Operación mínima: requiere intervención para cumplir su función'),
)
ESTADOS_EJECUCION = (
    ('adquirido', 'Adquirido'), ('en_proceso', 'En proceso de compra'), ('no_ejecutado', 'No ejecutado'),
)
TRIMESTRES = (('1', 'Primer trimestre'), ('2', 'Segundo trimestre'), ('3', 'Tercer trimestre'),
              ('4', 'Cuarto trimestre'))
ESTADOS_ACCION = (('pendiente', 'Pendiente'), ('en_curso', 'En curso'), ('cumplida', 'Cumplida'))
FUNDAMENTOS_INVERSION = (
    ('continuidad', 'Continuidad y mejora con resultados acreditados'),
    ('inicio', 'Puesta en funcionamiento de una unidad nueva'),
    ('capacidad', 'Dotación mínima para superar una limitación de capacidad'),
    ('seguridad', 'Seguridad, reparación o reposición indispensable'),
    ('recuperacion', 'Recuperación del uso mediante acciones de mejora'),
)

SECCIONES = {
    'planificacion': (
        Seccion('general', 'Información general de la unidad',
                'Sale de la ficha institucional de la unidad; si algo está desactualizado se corrige en la ficha, '
                'no aquí.', (
                    Campo('telefono', 'Teléfono de contacto', 'texto', ayuda='Extensión o celular institucional.'),
                    Campo('resolucion', 'Resolución de creación o aprobación', 'texto',
                          ayuda='Número y fecha; si la unidad no la tiene, déjalo en blanco.'),
                ), automatico='general'),
        Seccion('identidad', 'Descripción, misión, visión, políticas y estructura',
                'Descripción, misión, visión, políticas, organización y funciones de la unidad. '
                'Vincula el organigrama y el manual de funciones aprobados cuando existan.', (
                    Campo('descripcion', 'Descripción de la unidad', 'rico', True,
                          ayuda='Se propone la descripción pública de la ficha; ajústala al período.'),
                    Campo('mision', 'Misión', 'rico', True),
                    Campo('vision', 'Visión', 'rico', True),
                    Campo('politicas', 'Políticas de funcionamiento', 'rico',
                          ayuda='Una por línea: horarios, acceso, uso de equipos, seguridad.'),
                    Campo('estructura', 'Estructura orgánica-funcional', 'rico', True,
                          ayuda='Quién responde por qué. Abajo están las personas registradas en la unidad.'),
                ), automatico='estructura'),
        Seccion('objetivos', 'Objetivos del período',
                'Lo que la unidad se propone lograr en este semestre.', (
                    Campo('objetivo_general', 'Objetivo general', 'rico', True),
                    Campo('objetivos_especificos', 'Objetivos específicos', 'rico', True,
                          ayuda='Uno por línea; deben poder verificarse al cierre.'),
                )),
        Seccion('alcance', 'Sectores, áreas de trabajo, servicios y productos',
                'Las áreas y los servicios registrados aparecen solos; añade lo que falte.', (
                    Campo('sectores', 'Sectores de aplicación', 'marcas', True, opciones=SECTORES),
                    Campo('areas_adicionales', 'Otras áreas de trabajo técnico', 'rico'),
                    Campo('servicios_adicionales', 'Otros servicios o productos', 'rico'),
                ), automatico='alcance'),
        Seccion('diagnostico', 'Estado actual, diagnóstico y necesidades',
                'El estado de los equipos se toma del inventario; el diagnóstico lo escribe la unidad.', (
                    Campo('estado_operativo', 'Estado operativo de la unidad', 'opcion', True,
                          opciones=ESTADOS_OPERATIVOS),
                    Campo('diagnostico', 'Diagnóstico', 'rico', True,
                          ayuda='Qué funciona, qué limita la operación y por qué.'),
                    Campo('necesidades', 'Necesidades prioritarias', 'rico', True),
                ), automatico='diagnostico'),
        Seccion('mejora_previa', 'Evaluación del período anterior y respuesta de la unidad',
                'Lo que la Dirección evaluó del período anterior: fortalezas, debilidades y recomendaciones. '
                'La unidad dice aquí cómo las atiende en este período; eso es lo primero que se evalúa de '
                'esta planificación.', (
                    Campo('respuesta_evaluacion', 'Cómo atiende la unidad las recomendaciones', 'rico',
                          ayuda='Una acción concreta por recomendación, con responsable y mes. Si no hubo '
                                'recomendaciones, se deja en blanco.'),
                ), automatico='mejora_previa'),
        Seccion('plan', 'Plan de actividades del período',
                'Las referencias del plan se proponen según las funciones, la capacidad y el tiempo disponible. '
                'Son referencias operativas internas, no cuotas numéricas confirmadas por la Universidad. '
                'La meta acordada queda como compromiso del semestre: una planificación firmada no se rebaja '
                'automáticamente al cambiar la propuesta. '
                'Los meses se calculan con el calendario académico y la programación registrada. Marca las actividades que la unidad realizará; las que no '
                'apliquen se dejan sin marcar: eso también es una decisión válida y auditable. El cumplimiento '
                'se medirá con los registros del sistema en el informe semestral.', (
                    Campo('actividades', 'Actividades', 'actividades', True),
                )),
        Seccion('uso_capacidad', 'Capacidad y compromiso de uso efectivo',
                'Programa las horas de actividad que la unidad puede atender con sus jornadas, aforo, recursos '
                'y personal. Distingue docencia, investigación, servicios y visitas; puede haber actividad fuera '
                'del calendario académico. El total se calcula desde los meses; no se impone una ocupación universal.', (
                    Campo('presupuesto_uso', 'Horas de uso efectivo previstas', 'presupuesto_uso'),
                )),
        Seccion('inventario', 'Inventario e inversión a la fecha',
                'Equipos, software y espacios registrados en la plataforma.', (
                    Campo('mobiliario', 'Mobiliario e infraestructura relevante', 'rico',
                          ayuda='Lo que no está en el inventario de equipos: mesones, campanas, redes, obra civil.'),
                    Campo('observaciones_inventario', 'Observaciones al inventario', 'rico'),
                ), automatico='inventario'),
        Seccion('inversion', 'Plan de presupuesto y compras del período',
                'Lo que la unidad necesita adquirir o contratar en el período para ejecutarlo: equipamiento, '
                'insumos, materiales, mantenimiento. El sistema sugiere lo que ve en el inventario y las '
                'existencias; cada ítem se justifica frente a la capacidad de la unidad. Si no requiere nada, '
                'se justifica con el inventario y las actividades.', (
                    Campo('inversion', 'Presupuesto del período', 'tabla', columnas=(
                        ('categoria', 'Categoría', 'opcion', CATEGORIAS_INVERSION),
                        ('item', 'Ítem', 'texto', ()),
                        ('cantidad', 'Cantidad', 'numero', ()),
                        ('justificacion', 'Justificación', 'texto', ()),
                        ('prioridad', 'Prioridad', 'opcion', PRIORIDADES),
                        ('costo_unitario', 'Costo unitario (USD)', 'numero', ()),
                        ('fuente', 'Fuente', 'opcion', FUENTES_FINANCIAMIENTO),
                    )),
                    Campo('sin_inversion_justificacion', 'Si la unidad no requiere compras este período, por qué',
                          'rico', ayuda='Con el inventario, la vida útil de los equipos y las actividades a la '
                                        'vista. Se deja en blanco cuando la tabla tiene ítems.'),
                ), automatico='inversion'),
        Seccion('cronograma', 'Cronograma del período',
                'Se calcula con el calendario académico, las prácticas y los mantenimientos programados; las actividades adicionales conservan sus meses previstos.', (), automatico='cronograma'),
        Seccion('firmas', 'Firmas de responsabilidad',
                'Identifica a quien elabora el documento. El envío y la aprobación se registran en la plataforma.', (
                    Campo('firma_nombre', 'Elaborado por', 'texto', True),
                    Campo('firma_cargo', 'Cargo', 'texto', True),
                    Campo('revisa_nombre', 'Revisado por', 'texto',
                          ayuda='Coordinación o decanato, si la unidad lo requiere.'),
                    Campo('revisa_cargo', 'Cargo de quien revisa', 'texto'),
                )),
    ),
    'compras': (
        Seccion('general', 'Información general', 'Sale de la ficha de la unidad; el plan es para el año siguiente.',
                (), automatico='general'),
        Seccion('sugerencias', 'Lo que el sistema ve en el inventario y las existencias',
                'Equipos obsoletos o averiados, vida útil de referencia, bajas sin reemplazo e insumos '
                'agotados. Es el punto de partida: la unidad lo confirma, lo amplía o lo descarta con motivo.',
                (), automatico='sugerencias'),
        Seccion('compras', 'Compras planificadas para el año siguiente',
                'Equipamiento nuevo o de reemplazo, software, insumos, materiales, mantenimiento y capacitación, '
                'con cantidad, costo, prioridad, fuente y trimestre previsto.', (
                    Campo('compras', 'Compras del año', 'tabla', columnas=(
                        ('categoria', 'Categoría', 'opcion', CATEGORIAS_INVERSION),
                        ('item', 'Ítem', 'texto', ()),
                        ('cantidad', 'Cantidad', 'numero', ()),
                        ('justificacion', 'Justificación', 'texto', ()),
                        ('prioridad', 'Prioridad', 'opcion', PRIORIDADES),
                        ('costo_unitario', 'Costo unitario (USD)', 'numero', ()),
                        ('fuente', 'Fuente', 'opcion', FUENTES_FINANCIAMIENTO),
                        ('trimestre', 'Trimestre', 'opcion', TRIMESTRES),
                    )),
                    Campo('sin_compras_justificacion', 'Si la unidad no requiere compras, por qué', 'rico',
                          ayuda='Con el inventario, la vida útil y las actividades a la vista. Se deja en blanco '
                                'cuando la tabla tiene ítems.'),
                )),
        Seccion('capacidad', 'Coherencia con la capacidad de la unidad',
                'Cada compra tiene que corresponder a lo que la unidad puede instalar, operar y mantener.', (
                    Campo('capacidad', 'Relación con la capacidad instalada, el personal y las actividades', 'rico',
                          True, ayuda='Espacio, energía, personal que lo opera, mantenimiento previsto y las '
                                      'actividades que lo justifican. Si no incorporas una necesidad crítica sugerida, '
                                      'identifica el código del activo y explica su reparación, cobertura o aplazamiento.'),
                )),
        Seccion('priorizacion', 'Fundamento y prioridad de la inversión',
                'El documento se revisa por integridad. La prioridad de una solicitud considera el último '
                'semestre cerrado y su planificación, sin exigir un informe futuro. Las unidades nuevas, '
                'las limitaciones de capacidad y las necesidades de seguridad se argumentan por separado. '
                'Si no se necesitan compras, la justificación es suficiente y no existe solicitud de fondos.', (
                    Campo('fundamento_inversion', 'Fundamento de la solicitud', 'opcion',
                          opciones=FUNDAMENTOS_INVERSION,
                          ayuda='Selecciona una excepción sólo cuando corresponda; no implica aprobación del gasto.'),
                    Campo('justificacion_inversion', 'Justificación y compromiso de aprovechamiento', 'rico',
                          ayuda='Explica la limitación o riesgo con su referencia de respaldo, qué podrá hacerse '
                                'con lo solicitado, quién lo operará y en qué plazo. Ante un desempeño bajo, '
                                'indica las acciones de mejora; no basta con declarar que habrá más uso.'),
                ), automatico='priorizacion_inversion'),
        Seccion('firmas', 'Firmas de responsabilidad', '', (
                    Campo('firma_nombre', 'Elaborado por', 'texto', True),
                    Campo('firma_cargo', 'Cargo', 'texto', True),
                    Campo('revisa_nombre', 'Revisado por', 'texto'),
                    Campo('revisa_cargo', 'Cargo de quien revisa', 'texto'),
                )),
    ),
    'informe': (
        Seccion('general', 'Información general', 'Sale de la ficha de la unidad y del período.', (),
                automatico='general'),
        Seccion('resumen', 'Resumen ejecutivo', 'En pocas líneas: qué hizo la unidad en el período y con qué '
                'resultado.', (
                    Campo('resumen_ejecutivo', 'Resumen ejecutivo', 'rico', True),
                )),
        Seccion('cumplimiento', 'Cumplimiento del plan del período',
                'Cada actividad planificada con su meta, lo que el sistema registró y lo que la unidad reporta. '
                'Si difieren, el PDF muestra ambos: así el informe es transparente.', (
                    Campo('cumplimiento', 'Cumplimiento', 'cumplimiento'),
                )),
        Seccion('uso', 'Uso de la unidad en el período',
                'Sesiones, horas y usuarios registrados en la plataforma.', (
                    Campo('analisis_uso', 'Análisis del uso', 'rico',
                          ayuda='Qué explican estas cifras: picos, meses sin uso, tipos de usuario atendidos.'),
                ), automatico='uso'),
        Seccion('logros', 'Logros del período', 'Resultados concretos, verificables.', (
                    Campo('logros', 'Logros', 'rico', True),
                )),
        Seccion('dificultades', 'Dificultades y limitaciones', 'Lo que impidió cumplir o dificultó la '
                'operación. Si no hubo, se deja vacío y el informe lo dice.', (
                    Campo('dificultades', 'Dificultades', 'rico'),
                )),
        Seccion('presupuesto', 'Ejecución presupuestal del período',
                'Lo que la planificación previó comprar y qué pasó con cada ítem.', (
                    Campo('ejecucion_presupuestal', 'Lo ejecutado frente a lo planificado', 'tabla', columnas=(
                        ('item', 'Ítem', 'texto', ()),
                        ('planificado', 'Planificado (USD)', 'numero', ()),
                        ('ejecutado', 'Ejecutado (USD)', 'numero', ()),
                        ('estado', 'Estado', 'opcion', ESTADOS_EJECUCION),
                        ('observacion', 'Observación', 'texto', ()),
                    )),
                ), automatico='presupuesto'),
        Seccion('mejora', 'Acciones de mejora',
                'Cada hallazgo con su acción, responsable, plazo y estado. Alimentan la carpeta Mejora continua.', (
                    Campo('acciones', 'Acciones de mejora', 'tabla', columnas=(
                        ('hallazgo', 'Hallazgo', 'texto', ()),
                        ('accion', 'Acción', 'texto', ()),
                        ('responsable', 'Responsable', 'texto', ()),
                        ('plazo', 'Plazo', 'texto', ()),
                        ('estado', 'Estado', 'opcion', ESTADOS_ACCION),
                    )),
                ), automatico='mejora'),
        Seccion('necesidades', 'Necesidades para el siguiente período', '', (
                    Campo('necesidades_siguiente', 'Necesidades', 'rico'),
                )),
        Seccion('anexos', 'Anexos y evidencias', 'Los documentos del expediente archivados en el período.', (),
                automatico='anexos'),
        Seccion('firmas', 'Firmas de responsabilidad', '', (
                    Campo('firma_nombre', 'Elaborado por', 'texto', True),
                    Campo('firma_cargo', 'Cargo', 'texto', True),
                    Campo('revisa_nombre', 'Revisado por', 'texto'),
                    Campo('revisa_cargo', 'Cargo de quien revisa', 'texto'),
                )),
    ),
}


# -- catálogo de actividades del plan -----------------------------------------

@dataclass(frozen=True)
class Actividad:
    codigo: str
    nombre: str
    indicador: str
    minimo: str
    tipos: tuple = ()      # bases de tipología a las que se propone; vacío: todas
    contador: str = ''     # clave de `registros_del_periodo` que la mide sola
    obligatoria: bool = False  # la exige la institución a toda unidad: viene marcada y no se quita
    segun_programacion: bool = False


ACTIVIDADES_PLAN = (
    Actividad('USO', 'Registro de todas las sesiones de uso en la plataforma',
              'Sesiones registradas', '100 % de las sesiones', (), 'sesiones', True),
    Actividad('MANTENIMIENTO', 'Mantenimiento preventivo y correctivo de equipos',
              'Mantenimientos completados', '≥ 80 % de lo programado en equipos críticos', (), 'mantenimientos',
              True),
    Actividad('INVENTARIO', 'Revisión del inventario de equipos, software, espacios e insumos',
              'Acta de revisión física con respaldo', '1 por período', (), 'inventarios', True),
    Actividad('SEGURIDAD', 'Inducción de seguridad a usuarios nuevos',
              'Usuarios nuevos con inducción vigente y documentada', '100 % de usuarios nuevos', (), 'habilitaciones', True),
    Actividad('INSPECCIONES', 'Inspecciones mensuales de seguridad y condiciones de operación',
              'Meses exigibles con inspección documentada', '100 % de meses al corte',
              ('laboratorios',), 'meses_inspeccion_cubiertos'),
    Actividad('CAPACITACION', 'Capacitación del personal de la unidad', 'Capacitaciones recibidas',
              '≥ 1 por período', (), 'gestion_capacitacion'),
    Actividad('DIFUSION', 'Difusión de servicios y resultados de la unidad',
              'Publicaciones, eventos o materiales de difusión', '≥ 1 por período', (), 'gestion_difusion'),
    Actividad('PRACTICAS', 'Prácticas académicas ejecutadas con asistencia y evidencias',
              'Prácticas validadas con asistencia y evidencias', '≥ 6 por período',
              ('laboratorios', 'plantas_piloto', 'centro_experimental'), 'practicas'),
    Actividad('GUIAS', 'Guías de práctica nuevas o actualizadas', 'Guías vigentes con aprobación y syllabus', '≥ 1 por período',
              ('laboratorios', 'plantas_piloto', 'centro_experimental'), 'guias'),
    Actividad('INVESTIGACION', 'Resultados de investigación aplicada y desarrollo tecnológico',
              'Productos obtenidos con respaldo verificado', '≥ 1 por período', (), 'resultados_verificados'),
    Actividad('SERVICIOS', 'Servicios de análisis, fabricación o maquila atendidos', 'Solicitudes completadas',
              'según demanda', ('laboratorios', 'plantas_piloto', 'centro_experimental'), 'servicios'),
    Actividad('PRODUCCION', 'Lotes de producción o procesos ejecutados', 'Lotes u órdenes cerradas',
              'según plan de producción', ('plantas_piloto',), 'gestion_produccion'),
    Actividad('TRANSFERENCIA', 'Transferencia tecnológica y vinculación con el sector productivo',
              'Transferencias o servicios aceptados con respaldo', '≥ 1 por período', (), 'transferencias_verificadas'),
    Actividad('ENSAYOS', 'Ensayos y parcelas experimentales', 'Ensayos establecidos y evaluados',
              'según plan experimental', ('centro_experimental',), 'gestion_ensayos'),
    Actividad('DESECHOS', 'Gestión de desechos peligrosos y especiales', 'Registros de desecho', '100 % de lo '
              'generado', ('laboratorios', 'plantas_piloto', 'centro_experimental'), 'desechos'),
    Actividad('BOLETINES', 'Boletines, informes o bases de datos publicados', 'Publicaciones', '≥ 1 por período',
              ('observatorios',), 'gestion_boletines'),
    Actividad('EVENTOS', 'Eventos de socialización de resultados', 'Eventos realizados', '≥ 1 por período',
              ('observatorios', 'centros_id'), 'gestion_eventos'),
    Actividad('PROYECTOS', 'Proyectos de investigación en ejecución', 'Proyectos activos', '≥ 1',
              ('centros_id',), 'gestion_proyectos'),
    Actividad('PUBLICACIONES', 'Publicaciones científicas y ponencias', 'Artículos y ponencias', '≥ 1 por período',
              ('centros_id',), 'gestion_publicaciones'),
    Actividad('PRACTICAS-PLAN', 'Prácticas académicas planificadas y aprobadas', 'Prácticas aprobadas con escenario y responsable',
              '≥ 6 por período', ('laboratorios', 'plantas_piloto', 'centro_experimental'), 'practicas_planificadas_aprobadas'),
    Actividad('PRESTAMOS', 'Préstamos de equipos', 'Préstamos entregados en el período', '', (), 'prestamos'),
    Actividad('EQUIPAMIENTO', 'Disponibilidad del equipamiento', 'Equipos disponibles en el inventario al corte',
              '', (), 'equipos_disponibles'),
    Actividad('INSUMOS', 'Registro de movimientos de insumos', 'Movimientos de insumos registrados en el período',
              '', (), 'movimientos_insumos'),
    Actividad('MEJORA', 'Seguimiento de acciones de mejora', 'Acciones concluidas con evidencia verificable', ''),
    Actividad('DATOS-ACTUALIZADOS', 'Actualización de series y fuentes del observatorio',
              'Series actualizadas con fuente y revisión técnica', '≥ 2 por período',
              ('observatorios',), 'gestion_datos_actualizados'),
    Actividad('CONTROL-CALIDAD', 'Control de calidad de los lotes finalizados',
              'Lotes finalizados con controles conformes y respaldo técnico', '100 % de lotes finalizados',
              ('plantas_piloto',), 'gestion_control_calidad'),
)


def actividades_para(unidad, *, version=3, funciones=None, capacidad=None):
    base = unidad.codigo_base
    actividades = [a for a in ACTIVIDADES_PLAN if not a.tipos or base in a.tipos or
        version >= 3 and a.codigo == 'INSPECCIONES' and base in ('plantas_piloto', 'centro_experimental')]
    if version < 3:
        return [a for a in actividades if a.codigo not in ('DATOS-ACTUALIZADOS', 'CONTROL-CALIDAD')]
    from apps.documentos.presentation.politica_metas_unidades import actividades_proporcionales
    return actividades_proporcionales(actividades, base, funciones=funciones, capacidad=capacidad)


# -- utilidades ----------------------------------------------------------------

def secciones_de(tipo, unidad=None, contenido=None):
    if tipo == 'protocolo':
        from .protocolo_seguridad import secciones
        return secciones(Campo, Seccion)
    if tipo not in SECCIONES:
        raise Http404('Este documento no se redacta con el editor.')
    secciones = SECCIONES[tipo]
    # Las redacciones emitidas conservan su esquema. El editor nuevo separa
    # la cobertura del semestre de la solicitud de compras del año siguiente.
    if tipo == 'planificacion' and (contenido is None or contenido.get('recursos_periodo_version') == 1):
        cobertura = Seccion('inversion', 'Recursos disponibles y cobertura de las actividades',
            'Revisa con qué recursos se ejecutarán las actividades del semestre. Las necesidades para el '
            'año siguiente se registran una sola vez en el plan anual de compras; aquí se consulta la '
            'propuesta correspondiente al año vigente y se explican las limitaciones y medidas de cobertura.', (
                Campo('cobertura_recursos', 'Cobertura, limitaciones y medidas para ejecutar las actividades',
                    'rico', True, ayuda='Indica qué cubren los recursos existentes, qué depende de la gestión '
                    'del plan anual vigente y cómo se atenderán las limitaciones. Una necesidad nueva para '
                    'el próximo año se incorpora en el plan anual, sin repetir aquí sus cantidades y costos.'),
                Campo('revision_recursos', 'Revisión de los recursos del semestre', 'opcion', True,
                    opciones=(('revisado', 'Revisé la cobertura y las limitaciones de las actividades'),)),
            ), automatico='inversion')
        secciones = tuple(cobertura if s.codigo == 'inversion' else s for s in secciones)
    if tipo == 'compras' and (contenido is None or contenido.get('pac_version') in (1, 2)):
        from .pac_universitario import COLUMNAS_PAC
        secciones = tuple(replace(s, descripcion='Necesidades de bienes y servicios para ejecutar desde enero '
            'del año siguiente. La convocatoria ordinaria es en mayo; el plazo concreto lo define Dirección. '
            'La exportación conserva las columnas del formato universitario, con clasificación pendiente '
            'cuando aún no se conoce.', campos=(
                Campo('centro_costo', 'Centro de costo agrupador', 'texto', ayuda='Nombre del centro de costo '
                    'que agrupa a la unidad en la matriz universitaria. Confírmalo con el área administrativa; '
                    'la dependencia solicitante se toma automáticamente de la ficha de la unidad.'),
                Campo('compras', 'Necesidades de bienes y servicios', 'tabla', columnas=COLUMNAS_PAC),
                Campo('sin_compras_justificacion', 'Si no se requieren adquisiciones para el año siguiente, por qué',
                    'rico', ayuda='Justifica la cobertura con el inventario y las actividades previstas.'),
            )) if s.codigo == 'compras' else s for s in secciones)
        if contenido is None or contenido.get('pac_version') == 2:
            secciones = (
                Seccion('general', 'Datos de la unidad', 'La unidad y el año de las compras se toman del sistema.',
                    (), automatico='general'),
                Seccion('diagnostico_compras', 'Diagnóstico por áreas',
                    'Revisa los equipos existentes, su estado y el uso registrado en los dos últimos semestres cerrados. '
                    'Las propuestas permiten sustentar reposiciones, dotación faltante y ampliaciones.',
                    (), automatico='diagnostico_compras'),
                Seccion('compras', 'Compras y programación',
                    'Indica qué se necesita, para qué área, por qué y en qué mes se prevé comprarlo. '
                    'El semestre se calcula con el mes: enero–junio o julio–diciembre. '
                    'Si la compra se divide en dos fechas, registra una fila con la cantidad de cada fecha.', (
                        Campo('compras', 'Compras previstas para el año siguiente', 'tabla', columnas=COLUMNAS_PAC),
                        Campo('sin_compras_justificacion', 'Si no se requieren compras, explica la cobertura', 'rico',
                            ayuda='Indica cómo los equipos y recursos disponibles cubren las actividades previstas.'),
                    )),
                next(s for s in SECCIONES['compras'] if s.codigo == 'firmas'),
            )
            if contenido is None or contenido.get('inversion_gestion_version') == 1:
                gestion = Seccion('gestion_inversion', 'Cumplimiento y aprovechamiento',
                    'El sistema contrasta el plan vigente, las entregas exigibles y el uso documentado. '
                    'Cuando existan incumplimientos acreditados o una unidad nueva aún sin plan conforme, '
                    'explica cómo se aprovecharán los recursos y concreta las acciones. '
                    'Si el plan ya es conforme, no necesitas repetirlo.', (
                        Campo('justificacion_uso_existente', 'Aprovechamiento actual y limitaciones', 'rico',
                            ayuda='Ejemplo: los equipos disponibles cubren las prácticas básicas; la nueva '
                            'dotación resolverá la limitación documentada del área. Explica también las '
                            'medidas para utilizar los recursos existentes antes de ampliar su capacidad.'),
                        Campo('acciones_cumplimiento', 'Acciones verificables de cumplimiento', 'tabla',
                            ayuda='Ejemplo: programar y ejecutar las actividades pendientes con el equipo o área '
                            'existente; responsable: coordinación; plazo: una fecha concreta; resultado: '
                            'registrar lo realizado frente a las metas del plan, horario real y participantes.', columnas=(
                            ('accion', 'Acción', 'texto', ()), ('responsable', 'Responsable', 'texto', ()),
                            ('plazo', 'Plazo (AAAA-MM-DD)', 'texto', ()),
                            ('resultado', 'Resultado o meta verificable', 'texto', ()))),
                    ), automatico='gestion_inversion')
                secciones = (*secciones[:2], gestion, *secciones[2:])
            if contenido and contenido.get('compras_resumen_version') == 1:
                por_codigo = {s.codigo: s for s in secciones}
                por_codigo['diagnostico_compras'] = replace(por_codigo['diagnostico_compras'],
                    titulo='Sustento por áreas', descripcion='Relaciona las necesidades con los recursos existentes, '
                    'las incidencias y el mantenimiento. El detalle completo se consulta en Recursos e inventario.')
                orden = ('general', 'compras', 'diagnostico_compras', 'gestion_inversion', 'firmas')
                secciones = tuple(por_codigo[codigo] for codigo in orden if codigo in por_codigo)
    if tipo == 'informe' and contenido and contenido.get('recursos_periodo_version') == 1:
        secciones = tuple(replace(s, titulo='Uso de recursos y ejecución del período',
            descripcion='Referencia anual vigente y egresos confirmados del semestre. El detalle '
            'complementario permite explicar partidas verificadas y sus respaldos; no constituye '
            'otro presupuesto ni una autorización de compra.') if s.codigo == 'presupuesto' else s for s in secciones)
    if unidad is not None and base_de(unidad) == 'observatorios':
        secciones = tuple(s for s in secciones if s.codigo != 'uso_capacidad')
    return secciones


def meses_del_tramo(inicio, fin):
    """[(numero, 'Mar'), ...] de los meses que cubre el período."""
    meses, anio, mes = [], inicio.year, inicio.month
    while (anio, mes) <= (fin.year, fin.month):
        meses.append((mes, MESES_CORTOS[mes]))
        anio, mes = (anio + (mes == 12), mes % 12 + 1)
    return meses


def _nombre(usuario):
    if not usuario:
        return ''
    return usuario.get_full_name() or usuario.get_username()


def _cantidad(valor):
    """Decimal sin ceros sobrantes: 300.000 → 300, 0.500 → 0.5."""
    try:
        return format(Decimal(str(valor)).normalize(), 'f')
    except (InvalidOperation, ValueError):
        return str(valor)


def _decimal(valor):
    try:
        return Decimal(str(valor).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def _meses_de_fechas(fechas, meses):
    permitidos = {m for m, _ in meses}
    return sorted({f.month for f in fechas if f and f.month in permitidos})


def equipos_de(unidad):
    return UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad),
                                      activa=True, fecha_baja__isnull=True).distinct()


def programacion_mantenimiento(unidad, inicio, fin):
    """Fechas de mantenimiento que los planes de los equipos fijan dentro del período.

    Cada plan tiene una frecuencia en días y una próxima ejecución: se proyecta
    hacia adelante hasta el fin del período. Si un plan no cae en el período por
    su frecuencia, no se inventan fechas de mantenimiento.
    """
    filas = []
    planes = (PlanMantenimientoEquipo.objects.filter(equipo__in=equipos_de(unidad), activo=True)
              .select_related('equipo', 'equipo__equipo').order_by('equipo__codigo_unidad', 'nombre'))
    for plan in planes:
        fechas = []
        fecha = plan.proxima_ejecucion
        paso = timedelta(days=max(plan.frecuencia_dias or 0, 1))
        while fecha < inicio:
            fecha += paso
        while fecha <= fin and len(fechas) < 31:
            fechas.append(fecha)
            fecha += paso
        filas.append({'plan': plan, 'equipo': plan.equipo, 'fechas': fechas})
    programados = MantenimientoEquipo.objects.filter(
        unidad=unidad, fecha_programada__date__range=(inicio, fin)).exclude(estado='cancelado')
    for mantenimiento in programados.select_related('equipo', 'equipo__equipo'):
        filas.append({'plan': None, 'mantenimiento': mantenimiento, 'equipo': mantenimiento.equipo,
                      'fechas': [timezone.localtime(mantenimiento.fecha_programada).date()]})
    return filas


def _bloque_mantenimientos(unidad, inicio, fin, *, solo_programados=False):
    filas = []
    for fila in programacion_mantenimiento(unidad, inicio, fin):
        if solo_programados and fila.get('mantenimiento') and fila['mantenimiento'].tipo == 'correctivo':
            continue
        plan = fila.get('plan')
        if plan is not None:
            descripcion = f"{plan.nombre} · {plan.get_tipo_display()}"
            frecuencia = f'cada {plan.frecuencia_dias} días'
        else:
            mantenimiento = fila['mantenimiento']
            descripcion = f"{mantenimiento.titulo} · {mantenimiento.get_tipo_display()}"
            frecuencia = 'orden programada'
        fechas = ', '.join(f'{f:%d/%m}' for f in fila['fechas']) or 'fuera del período'
        filas.append([str(fila['equipo']), descripcion, frecuencia, fechas])
    return {'tipo': 'tabla', 'titulo': 'Mantenimientos previstos por los planes de los equipos',
            'cabecera': ['Equipo', 'Plan', 'Frecuencia', 'Fechas en el período'], 'filas': filas}


ACTIVIDADES_DOCENTES = frozenset({'PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS'})
ORDEN_PLAN = ('USO', 'PRACTICAS-PLAN', 'PRACTICAS', 'GUIAS', 'SEGURIDAD', 'INSPECCIONES',
    'DESECHOS', 'INVENTARIO', 'INVESTIGACION', 'TRANSFERENCIA', 'SERVICIOS',
    'MANTENIMIENTO', 'CAPACITACION', 'DIFUSION')


def _calendario_docente(inicio, fin, documento=None):
    """Calendario publicado del mismo año/ciclo; no redefine el tramo de gestión."""
    from apps.core.models.periodos import PeriodoAcademico

    anio = getattr(documento, 'anio', None) or inicio.year
    ciclo = getattr(documento, 'corte', None) or ('A' if inicio.month <= 6 else 'B')
    periodos = PeriodoAcademico.objects.operativos().publicados().filter(
        anio_referencia=anio, ciclo=ciclo, tipo='ordinario').prefetch_related('versiones').order_by('codigo', 'pk')
    candidatos = [(p, p.version_vigente) for p in periodos]
    candidatos = [(p, v) for p, v in candidatos if v is not None]
    if not candidatos:
        return dict(disponible=False, aviso='Calendario académico pendiente de publicar para este año y ciclo.')
    if len({(v.fecha_inicio_clases, v.fecha_fin_clases) for _, v in candidatos}) > 1:
        return dict(disponible=False, aviso='Hay calendarios académicos publicados con fechas distintas para este ciclo; revisa el calendario institucional aplicable.')
    periodo, version = candidatos[0]
    desde, hasta = max(inicio, version.fecha_inicio_clases), min(fin, version.fecha_fin_clases)
    return dict(disponible=True, periodo_codigo=periodo.codigo, periodo_id=periodo.pk,
        version_calendario=version.pk, numero_version=version.numero,
        clases_inicio=version.fecha_inicio_clases.isoformat(), clases_fin=version.fecha_fin_clases.isoformat(),
        meses=[m for m, _ in meses_del_tramo(desde, hasta)] if desde <= hasta else [])


def cronograma_automatico(unidad, inicio, fin, *, documento=None):
    """Propuesta verificable por actividad, preparada una vez por lectura/guardado.

    Las fechas docentes se cruzan con el calendario académico; una práctica
    realmente programada dentro del tramo se conserva aunque sea interperíodo.
    Mantenimiento usa planes y órdenes reales y nunca inventa un mes de control.
    """
    meses = meses_del_tramo(inicio, fin)
    todos = [m for m, _ in meses]
    calendario = _calendario_docente(inicio, fin, documento)
    mantenimiento_por_equipo = programacion_mantenimiento(unidad, inicio, fin)
    particulares = [fila for fila in mantenimiento_por_equipo
                   if not fila.get('mantenimiento') or fila['mantenimiento'].tipo != 'correctivo']
    programados = [f for fila in particulares for f in fila['fechas'] if f and inicio <= f <= fin]
    practicas = list(PlanificacionPractica.objects.filter(
        unidad=unidad, fecha__range=(inicio, fin), eliminado_en__isnull=True).values_list('fecha', flat=True))
    docentes = list(calendario.get('meses') or [])
    reales = _meses_de_fechas(practicas, meses)
    equipos_exigibles = bool(programados or equipos_de(unidad).exists())
    ventana = None
    if equipos_exigibles and calendario.get('disponible'):
        clases_inicio = date.fromisoformat(calendario['clases_inicio'])
        clases_fin = date.fromisoformat(calendario['clases_fin'])
        antes = min(fin, clases_inicio - timedelta(days=1))
        while antes >= inicio and antes.weekday() >= 5:
            antes -= timedelta(days=1)
        despues = max(inicio, clases_fin + timedelta(days=1))
        while despues <= fin and despues.weekday() >= 5:
            despues += timedelta(days=1)
        ventana = antes if antes >= inicio else despues if despues <= fin else None
    mantenimiento = [ventana.month] if ventana else []
    previstos = {a.codigo: list(todos) for a in actividades_para(unidad)}
    previstos.update(MANTENIMIENTO=mantenimiento, INVENTARIO=todos[-1:],
        PRACTICAS=list(reales or docentes), **{'PRACTICAS-PLAN': list(reales or docentes), 'GUIAS': docentes})
    origenes = {codigo: 'Seguimiento durante todo el semestre de gestión.' for codigo in previstos}
    origenes['INVENTARIO'] = 'Revisión de inventario al cierre del tramo del documento.'
    origenes['MANTENIMIENTO'] = (
        f'Ventana preventiva general propuesta: {ventana:%d/%m/%Y}, fuera de clases. Una intervención general por semestre; '
        'cada equipo conserva su frecuencia técnica y sus órdenes propias. Los correctivos se informan por separado.' if ventana else
        'No hay una ventana general fuera de clases dentro del tramo. Programa por equipo sin interferir con su uso; '
        'los correctivos se informan por separado.' if equipos_exigibles else
        'Sin programación exigible: no hay equipos activos ni órdenes de mantenimiento en el tramo.')
    for codigo in ACTIVIDADES_DOCENTES:
        origenes[codigo] = ('Calendario académico publicado, limitado al tramo del documento.' if docentes else
            'El calendario académico publicado no tiene clases dentro del tramo del documento.')
        if not calendario.get('disponible'):
            origenes[codigo] = calendario['aviso']
    if reales:
        for codigo in ('PRACTICAS', 'PRACTICAS-PLAN'):
            origenes[codigo] = ('Fechas reales de las prácticas programadas en el tramo.' +
                (' Incluye programación fuera de los meses de clases.' if set(reales) - set(docentes) else ''))
    avisos = [] if calendario.get('disponible') else [calendario['aviso']]
    if equipos_exigibles and not mantenimiento and not programados:
        avisos.append(origenes['MANTENIMIENTO'])
    return dict(version=1, gestion_inicio=inicio.isoformat(), gestion_fin=fin.isoformat(),
        calendario_disponible=bool(calendario.get('disponible')), meses_academicos=docentes,
        periodo_codigo=calendario.get('periodo_codigo', ''),
        version_calendario=calendario.get('version_calendario'),
        numero_version=calendario.get('numero_version'),
        clases_inicio=calendario.get('clases_inicio'), clases_fin=calendario.get('clases_fin'),
        meses_por_actividad=previstos, origenes=origenes,
        mantenimiento_exigible=equipos_exigibles, avisos=avisos,
        mantenimiento_ventana=ventana.isoformat() if ventana else None,
        mantenimiento_meses_por_equipo=_meses_de_fechas(programados, meses),
        descripcion='Docencia según calendario académico; una ventana preventiva general fuera de clases. Las frecuencias específicas y los correctivos se consultan en mantenimiento.')


def meses_por_defecto(unidad, inicio, fin, *, documento=None, historico=False):
    if historico:
        # Compatibilidad de lectura: una planificación sin la nueva versión
        # del cronograma conserva las reglas con las que se redactó. Solo un
        # guardado explícito desde el editor adopta el calendario automático.
        meses = meses_del_tramo(inicio, fin)
        todos = [m for m, _ in meses]
        programados = [f for fila in programacion_mantenimiento(unidad, inicio, fin) for f in fila['fechas']]
        practicas = list(PlanificacionPractica.objects.filter(
            unidad=unidad, fecha__range=(inicio, fin), eliminado_en__isnull=True).values_list('fecha', flat=True))
        previstos = dict(MANTENIMIENTO=_meses_de_fechas(programados, meses)
            or todos[len(todos) // 2:len(todos) // 2 + 1], INVENTARIO=todos[-1:],
            PRACTICAS=_meses_de_fechas(practicas, meses))
        for actividad in actividades_para(unidad):
            if actividad.obligatoria and not previstos.get(actividad.codigo):
                previstos[actividad.codigo] = list(todos)
        return previstos
    return cronograma_automatico(unidad, inicio, fin, documento=documento)['meses_por_actividad']


def _aplicar_cronograma(plan, cronograma):
    """Copia de edición: no modifica planes firmados ni asignaciones guardadas."""
    actualizado = deepcopy(plan)
    for codigo, fila in (actualizado.get('catalogo') or {}).items():
        if isinstance(fila, dict):
            fila['meses'] = list(cronograma['meses_por_actividad'].get(codigo, [])) if fila.get('aplica') else []
    meses_del_periodo = [m for m, _ in meses_del_tramo(
        date.fromisoformat(cronograma['gestion_inicio']), date.fromisoformat(cronograma['gestion_fin']))]
    for fila in actualizado.get('otras') or []:
        if isinstance(fila, dict) and 'meses' not in fila:
            fila['meses'] = list(meses_del_periodo)
    actualizado['cronograma_auto'] = deepcopy(cronograma)
    return actualizado


def plan_inicial(documento, inicio, fin):
    """Las actividades obligatorias vienen marcadas, con su mínimo como meta y su cronograma
    tomado de lo ya programado (mantenimientos, prácticas); lo demás queda a decisión de la unidad."""
    unidad = documento.unidad
    from apps.documentos.presentation.politica_metas_unidades import capacidad_de, propuesta_del_semestre
    capacidad = capacidad_de(unidad, inicio, fin)
    cronograma = cronograma_automatico(unidad, inicio, fin, documento=documento)
    previstos = cronograma['meses_por_actividad']
    practicas = previstos.get('PRACTICAS') or []
    numero_practicas = PlanificacionPractica.objects.filter(
        unidad=unidad, fecha__range=(inicio, fin), eliminado_en__isnull=True,
        estado='aprobada').count()
    catalogo = {}
    for actividad in actividades_para(unidad, capacidad=capacidad):
        requerida = actividad.obligatoria or obligatoria_por_tipo(actividad)
        fila = {'aplica': requerida, 'meta': propuesta_del_semestre(capacidad, actividad) if requerida else '',
                'meses': list(previstos.get(actividad.codigo, [])) if requerida else [],
                'responsable': ''}
        if actividad.codigo in ('PRACTICAS', 'PRACTICAS-PLAN') and numero_practicas:
            fila.update({'aplica': True, 'meta': str(max(capacidad['practicas_recomendadas'], numero_practicas)),
                         'meses': list(practicas)})
        catalogo[actividad.codigo] = fila
    from .metas_estandar import aplicar_metas, calcular_metas
    return aplicar_metas({'catalogo': catalogo, 'otras': [], 'minimos_catalogo': 3, 'capacidad': capacidad,
            'cronograma_auto': cronograma}, calcular_metas(unidad, inicio, fin,
                actividades_para(unidad, capacidad=capacidad), capacidad, cronograma))


def valores_iniciales(documento):
    """Lo que el editor propone la primera vez: redacciones base para el tipo de unidad,
    el plan con lo obligatorio ya marcado y quién firma. La unidad lo ajusta."""
    from apps.documentos.presentation.expediente import tramo_del_documento

    unidad = documento.unidad
    tipo = documento.exigido.fuente_reporte
    if tipo == 'protocolo':
        from .protocolo_seguridad import valores_iniciales as iniciales_protocolo
        return iniciales_protocolo(documento)
    inicio, fin = tramo_del_documento(documento)
    sugeridos = sugerencias_para(documento, POLITICAS_RICAS)
    contenido = {'firma_nombre': _nombre(unidad.administrador), 'firma_cargo': 'Responsable de la unidad'}
    for seccion in secciones_de(tipo):
        for campo in seccion.campos:
            if campo.tipo == 'rico' and sugeridos.get(campo.clave):
                contenido[campo.clave] = sugeridos[campo.clave][0]['html']
            elif campo.tipo == 'actividades':
                contenido[campo.clave] = plan_inicial(documento, inicio, fin)
    if tipo == 'planificacion':
        from .recursos_periodo import preparar_recursos
        contenido = preparar_recursos(contenido)
    elif tipo == 'compras':
        from .pac_universitario import preparar_pac
        contenido = preparar_pac(contenido, unidad=unidad)
    elif tipo == 'informe':
        plan = planificacion_del_periodo(documento)
        if plan is not None and (plan.contenido or {}).get('recursos_periodo_version') == 1:
            contenido['recursos_periodo_version'] = 1
    return contenido


def obtener_redaccion(documento):
    """La redacción del documento; mientras nadie la haya guardado, se completa con lo propuesto."""
    redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first() or DocumentoElaborado(
        documento=documento)
    if redaccion.version == 0:
        propuesto = valores_iniciales(documento)
        actual = dict(redaccion.contenido or {})
        for clave, valor in propuesto.items():
            if not actual.get(clave):
                actual[clave] = valor
        if actual != redaccion.contenido:
            redaccion.contenido = actual
    if documento.exigido.fuente_reporte == 'protocolo' and documento.estado not in ('validado', 'cargado'):
        from .protocolo_contexto import completar_contenido
        redaccion.contenido = completar_contenido(documento, redaccion.contenido, proponer=True)
    if documento.estado not in ('validado', 'cargado', 'generado'):
        if documento.exigido.fuente_reporte == 'planificacion':
            from .recursos_periodo import preparar_recursos
            redaccion.contenido = preparar_recursos(redaccion.contenido)
        elif documento.exigido.fuente_reporte == 'compras':
            from .pac_universitario import preparar_pac
            redaccion.contenido = preparar_pac(redaccion.contenido, unidad=documento.unidad)
    return redaccion


# -- leer lo que la unidad escribió -------------------------------------------

def leer_formulario(tipo, post, unidad, *, inicio=None, fin=None, documento=None, contenido_anterior=None):
    """Convierte lo enviado por el editor en el diccionario de contenido."""
    contenido = {}
    for seccion in secciones_de(tipo):
        for campo in seccion.campos:
            contenido[campo.clave] = _leer_campo(campo, post, unidad, inicio=inicio, fin=fin,
                documento=documento, anterior=(contenido_anterior or {}).get(campo.clave))
    if tipo == 'protocolo':
        from types import SimpleNamespace
        from .protocolo_contexto import leer_contenido
        return leer_contenido(documento or SimpleNamespace(unidad=unidad), contenido, contenido_anterior, post)
    if tipo == 'planificacion':
        from .recursos_periodo import preparar_recursos
        # Conserva las previsiones antiguas como antecedentes, sin recapturarlas.
        anteriores = contenido_anterior or {}
        for clave in ('inversion', 'sin_inversion_justificacion'):
            if clave in anteriores:
                contenido[clave] = deepcopy(anteriores[clave])
        contenido['recursos_periodo_version'] = 1
        contenido = preparar_recursos(contenido)
    elif tipo == 'compras':
        from .pac_universitario import leer_pac
        contenido.update(leer_pac(post, contenido_anterior or {}, unidad=unidad))
    return contenido


def politica_de(campo):
    """Qué admite la zona enriquecida: «texto» (párrafos, listas, énfasis) o «tablas» (además subtítulos y tablas)."""
    return POLITICAS_RICAS.get(campo.clave, 'texto')


def html_del_campo(campo, valor):
    """HTML acotado del campo; convierte lo escrito antes como texto plano o lista."""
    if isinstance(valor, (list, tuple)):
        valor = '\n'.join(str(v) for v in valor)
    valor = str(valor or '')
    if valor and not valor.lstrip().startswith('<'):
        valor = texto_a_html(valor, politica_de(campo))
    return valor


def _leer_campo(campo, post, unidad, *, inicio=None, fin=None, documento=None, anterior=None):
    if campo.tipo == 'rico':
        return sanear(post.get(campo.clave, ''), politica_de(campo))[0]
    if campo.tipo == 'texto':
        return post.get(campo.clave, '').strip()
    if campo.tipo == 'opcion':
        valor = post.get(campo.clave, '')
        return valor if valor in dict(campo.opciones) else ''
    if campo.tipo == 'marcas':
        permitidos = dict(campo.opciones)
        return [v for v in post.getlist(campo.clave) if v in permitidos]
    if campo.tipo == 'tabla':
        columnas = [post.getlist(f'{campo.clave}__{col}') for col, *_ in campo.columnas]
        filas = []
        # Una columna que el formulario no envía (agregada después) no borra las filas.
        for valores in zip_longest(*columnas, fillvalue=''):
            fila = {}
            for (col, _etq, tipo_col, opciones), valor in zip(campo.columnas, valores):
                valor = valor.strip()
                if tipo_col == 'opcion' and valor not in dict(opciones):
                    valor = ''
                fila[col] = valor
            if any(fila.values()):
                filas.append(fila)
        return filas
    if campo.tipo == 'actividades':
        return _leer_actividades(post, unidad, inicio=inicio, fin=fin, documento=documento, anterior=anterior)
    if campo.tipo == 'presupuesto_uso':
        from .presupuesto_uso import leer_presupuesto
        return leer_presupuesto(post, inicio, fin) if inicio and fin and post.get('uso_presupuesto_presente') else {}
    if campo.tipo == 'cumplimiento':
        return _leer_cumplimiento(post)
    return post.get(campo.clave, '').strip()


def _meses_validos(valores):
    meses = []
    for v in valores:
        if str(v).isdigit() and 1 <= int(v) <= 12 and int(v) not in meses:
            meses.append(int(v))
    return sorted(meses)


def _leer_actividades(post, unidad, *, inicio=None, fin=None, documento=None, anterior=None):
    from apps.documentos.presentation.politica_metas_unidades import capacidad_de
    capacidad = capacidad_de(unidad, inicio, fin)
    cronograma = cronograma_automatico(unidad, inicio, fin, documento=documento) if inicio and fin else None
    anterior = anterior if isinstance(anterior, dict) else {}
    catalogo_anterior = anterior.get('catalogo') if isinstance(anterior.get('catalogo'), dict) else {}
    actividades = list(actividades_para(unidad, funciones=post.getlist('sectores'), capacidad=capacidad))
    from .metas_estandar import calcular_metas
    politica = calcular_metas(unidad, inicio, fin, actividades, capacidad, cronograma) if cronograma else None
    catalogo = {}
    for actividad in actividades:
        prefijo = f'act__{actividad.codigo}__'
        if actividad.codigo in ANEXOS_AUTOMATICOS:
            catalogo[actividad.codigo] = dict(aplica=False, obligatoria=False, meta='', meses=[], responsable='')
            continue
        exigencia = post.get(prefijo + 'exigencia')
        if exigencia is not None and exigencia not in ('obligatoria', 'opcional', 'no_aplica'):
            raise ValidationError('Selecciona una exigencia válida para cada actividad.')
        requerida = actividad.obligatoria or obligatoria_por_tipo(actividad)
        aplica = requerida or (exigencia != 'no_aplica' if exigencia is not None
                                           else post.get(prefijo + 'aplica') == '1')
        catalogo[actividad.codigo] = {
            'aplica': aplica,
            'obligatoria': requerida or (aplica and exigencia != 'opcional'),
            'meta': ((politica['metas'][actividad.codigo] if politica and actividad.codigo in politica['metas']
                      else meta_con_minimo(actividad, post.get(prefijo + 'meta', ''))) if aplica
                     else post.get(prefijo + 'meta', '').strip()),
            'meses': (list(cronograma['meses_por_actividad'].get(actividad.codigo, [])) if aplica else [])
                if cronograma else _meses_validos(post.getlist(prefijo + 'meses')),
            'responsable': (str((catalogo_anterior.get(actividad.codigo) or {}).get('responsable') or '')
                if prefijo + 'responsable' not in post else post.get(prefijo + 'responsable', '')).strip(),
        }
    otras = []
    nombres = post.getlist('otra__nombre')
    indicadores = post.getlist('otra__indicador')
    metas = post.getlist('otra__meta')
    responsables = post.getlist('otra__responsable')
    for indice, nombre in enumerate(nombres):
        if not nombre.strip():
            continue
        otras.append({
            'nombre': nombre.strip(),
            'indicador': (indicadores[indice] if indice < len(indicadores) else '').strip(),
            'meta': (metas[indice] if indice < len(metas) else '').strip(),
            'responsable': (responsables[indice] if indice < len(responsables) else
                str((anterior.get('otras') or [])[indice].get('responsable') or '')
                if indice < len(anterior.get('otras') or []) else '').strip(),
            'meses': (_meses_validos(post.getlist(f'otra__meses__{indice}'))
                if post.getlist(f'otra__meses__{indice}') or post.get(f'otra__meses_presentes__{indice}') == '1'
                or not cronograma else [m for m, _ in meses_del_tramo(inicio, fin)]),
        })
    resultado = {'catalogo': catalogo, 'otras': otras, 'minimos_catalogo': 3, 'capacidad': capacidad}
    if cronograma:
        resultado['cronograma_auto'] = cronograma
        resultado['metas_estandar'] = politica
    return resultado


def _leer_cumplimiento(post):
    resultado = {}
    for clave in post.keys():
        if clave.startswith('cum__') and clave.endswith('__realizado'):
            codigo = clave[len('cum__'):-len('__realizado')]
            resultado[codigo] = {
                'realizado': post.get(clave, '').strip(),
                'observacion': post.get(f'cum__{codigo}__observacion', '').strip(),
            }
    return resultado


# -- avance y faltantes --------------------------------------------------------

def avance(tipo, contenido):
    """{'porcentaje', 'faltantes': [(seccion, campo)], 'secciones': {codigo: completa}}."""
    from .validacion_campos_documentales import validar_campos
    secciones = secciones_de(tipo, contenido=contenido if isinstance(contenido, dict) else {})
    hallazgos = validar_campos(tipo, contenido, secciones)
    contenido = contenido if isinstance(contenido, dict) else {}
    invalidos = {h['clave'] for h in hallazgos}
    requeridos, llenos, faltantes, por_seccion, detalles = 0, 0, [], {}, []
    detalles.extend(h['mensaje'] for h in hallazgos)
    for seccion in secciones:
        completa = True
        for campo in seccion.campos:
            if not campo.requerido and not (campo.tipo == 'tabla' and contenido.get(campo.clave)) and campo.clave not in invalidos:
                continue
            if campo.clave in ('inversion', 'compras'):
                continue
            requeridos += 1
            completo = campo.clave not in invalidos
            if completo:
                llenos += 1
            else:
                completa = False
                faltantes.append((seccion, campo))
        por_seccion[seccion.codigo] = completa
    # El presupuesto se declara o se justifica su ausencia: una de las dos, nunca ninguna.
    for seccion_codigo, tabla in (('inversion', 'inversion'), ('compras', 'compras')):
        if tipo == 'planificacion' and contenido.get('recursos_periodo_version') == 1:
            continue
        seccion = next((s for s in secciones if s.codigo == seccion_codigo), None)
        if seccion is None:
            continue
        campo_tabla = next(c for c in seccion.campos if c.clave == tabla)
        requeridos += 1
        presupuesto = analizar_presupuesto(tipo, contenido)
        if presupuesto['completo']:
            llenos += 1
        else:
            por_seccion[seccion.codigo] = False
            faltantes.append((seccion, campo_tabla))
            detalles.extend(h['mensaje'] for h in presupuesto['hallazgos'] if h['severidad'] == 'bloqueo')
    porcentaje = round(100 * llenos / requeridos) if requeridos else 100
    return {'porcentaje': porcentaje, 'faltantes': faltantes, 'secciones': por_seccion,
            'requeridos': requeridos, 'llenos': llenos, 'detalles': detalles}


def faltantes_del_editor(progreso):
    """Secciones pendientes con el detalle necesario para corregirlas."""
    return [f'{s.titulo} → {c.etiqueta}' for s, c in progreso['faltantes']] + progreso.get('detalles', [])


# -- lo que el sistema ya sabe ---------------------------------------------------

def registros_del_periodo(unidad, inicio, fin):
    """Conteos del período, desde los registros reales. Son los que miden el plan."""
    reservas = Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin)).exclude(
        estado__in=ESTADOS_RESERVA_DESCARTADOS)
    candidatas = reservas.filter(estado__in=ESTADOS_ATENCION_EFECTIVA).only(
        'estado', 'resultado_cierre', 'hora_inicio', 'hora_fin', 'detalle_ejecucion', 'proposito_codigo')
    atendidas = investigacion_atendida = 0
    horas = 0.0
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas
    for reserva in candidatas.iterator(chunk_size=200):
        if not reserva.es_efectiva:
            continue
        atendidas += 1
        investigacion_atendida += reserva.proposito_codigo in ('investigacion_innovacion', 'titulacion')
        horas += horas_efectivas(reserva)
    por_tipo = Counter()
    for tipo in reservas.values_list('usuario__profile__tipo_usuario', flat=True):
        por_tipo[tipo or 'sin_tipo'] += 1
    por_proposito = Counter(reservas.values_list('proposito_codigo', flat=True))
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True).distinct()
    mantenimientos = MantenimientoEquipo.objects.filter(unidad=unidad)
    from apps.documentos.presentation.medicion_metas import registros_de_gestion
    datos = {
        'sesiones': reservas.count(),
        'atendidas': atendidas,
        'horas': round(horas, 1),
        'usuarios': reservas.values('usuario').distinct().count(),
        'usuarios_por_tipo': dict(por_tipo),
        'por_proposito': dict(por_proposito),
        'practicas_planificadas': PlanificacionPractica.objects.filter(
            unidad=unidad, fecha__range=(inicio, fin), eliminado_en__isnull=True).count(),
        'practicas_planificadas_aprobadas': PlanificacionPractica.objects.filter(
            unidad=unidad, fecha__range=(inicio, fin), eliminado_en__isnull=True,
            estado='aprobada', es_version_vigente=True).count(),
        'practicas': EjecucionPractica.objects.filter(
            planificacion__unidad=unidad, fecha_ejecucion__range=(inicio, fin), estado='validada',
            resultado='ejecutada', eliminado_en__isnull=True).count(),
        'guias': GuiaActividadReserva.objects.filter(
            actividad__unidad=unidad, activo=True, estado_publicacion='publicada',
            actualizado_en__date__range=(inicio, fin)).count(),
        'mantenimientos': mantenimientos.filter(estado='completado', fecha_fin__date__range=(inicio, fin)).count(),
        'mantenimientos_programados': mantenimientos.filter(fecha_programada__date__range=(inicio, fin)).count(),
        'mantenimientos_criticos_programados': mantenimientos.filter(
            equipo__criticidad='critico', fecha_programada__date__range=(inicio, fin)).count(),
        'mantenimientos_criticos_cumplidos': mantenimientos.filter(
            equipo__criticidad='critico', fecha_programada__date__range=(inicio, fin),
            estado='completado', fecha_fin__date__range=(inicio, fin)).count(),
        'incidencias': IncidenciaEquipo.objects.filter(
            unidad=unidad, fecha_reporte__date__range=(inicio, fin)).count(),
        'habilitaciones': HabilitacionAcceso.objects.filter(
            requisito__unidad=unidad, fecha__range=(inicio, fin)).count(),
        'servicios': SolicitudFabricacion.objects.filter(
            unidad=unidad, estado='completada', fecha_solicitud__range=(inicio, fin)).count(),
        'investigacion': reservas.filter(proposito_codigo__in=('investigacion_innovacion', 'titulacion')).count(),
        'investigacion_atendida': investigacion_atendida,
        'desechos': RegistroDesecho.objects.filter(unidad=unidad, fecha_generacion__range=(inicio, fin)).count(),
        'inventarios': DocumentoExpediente.objects.filter(
            unidad=unidad, exigido__codigo='INVENTARIO-CORTE', estado__in=('generado', 'validado'),
            recurso__isnull=False, vence_el__range=(inicio, fin)).count(),
        'equipos_total': equipos.count(),
        'equipos_disponibles': equipos.filter(estado_unidad='disponible').count(),
        'prestamos': PrestamoEquipo.objects.filter(
            unidad=unidad, fecha_salida__date__range=(inicio, fin),
            estado__in=('entregado', 'devuelto', 'no_devuelto')).count(),
        'movimientos_insumos': EntradaInventario.objects.filter(
            consumible__unidad=unidad, fecha__date__range=(inicio, fin), cantidad__gt=0).count(),
        **registros_de_gestion(unidad, inicio, fin),
    }
    from apps.documentos.presentation.cumplimiento_practicas import conteos_del_periodo
    datos.update(conteos_del_periodo(unidad, inicio, fin))
    return datos


def _pares_generales(documento, inicio, fin):
    unidad = documento.unidad
    responsables = list(ResponsableUnidad.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre'))
    administrador = unidad.administrador
    return [
        ('Tipo de unidad', unidad.nombre_tipologia or (unidad.dependencia or '').replace('_', ' ').title()),
        ('Nombre', unidad.nombre),
        ('Código institucional', unidad.codigo or '—'),
        ('Clasificación funcional', unidad.get_clasificacion_funcional_display() or '—'),
        ('Área de conocimiento', unidad.get_area_conocimiento_display() or '—'),
        ('Facultad', unidad.facultad or '—'),
        ('Carreras que atiende', unidad.carreras or '—'),
        ('Administrador responsable', f'{_nombre(administrador)}'
         + (f' · {administrador.email}' if administrador and administrador.email else '') if administrador else '—'),
        ('Equipo de la unidad', '; '.join(f'{r.nombre} ({r.get_rol_display()})' for r in responsables) or '—'),
        ('Correo de contacto', unidad.contacto_email or '—'),
        ('Ubicación', unidad.ubicacion or '—'),
        ('Horario de atención', unidad.horario_atencion or '—'),
        ('Período', f'{documento.etiqueta_corte} · {inicio:%d/%m/%Y} – {fin:%d/%m/%Y}'),
        ('Fecha de elaboración', f'{timezone.localdate():%d/%m/%Y}'),
    ]


def _pares_uso_informe(unidad, registros):
    """Un resumen de las fuentes del perfil; el detalle permanece en sus anexos."""
    def valor(clave):
        return str(registros[clave]) if clave in registros else 'Sin medición disponible'

    pares = [
        ('Sesiones registradas', valor('sesiones')),
        ('Sesiones atendidas', valor('atendidas')),
        ('Horas de uso efectivas', f"{registros['horas']:g}" if 'horas' in registros else valor('horas')),
        ('Usuarios distintos', valor('usuarios')),
    ]
    # Las cifras de cada meta (prácticas, guías, desechos, mantenimiento…) están una sola vez, en el
    # apartado de cumplimiento y en su anexo; aquí solo el uso, para que no haya dos cifras distintas.
    base = base_de(unidad)
    pares.append(('Incidencias de equipos reportadas', valor('incidencias')))
    indicadores = {
        'observatorios': (
            ('Publicaciones con revisión técnica', 'gestion_boletines'),
            ('Actualizaciones de series con revisión técnica', 'gestion_datos_actualizados'),
            ('Socializaciones con revisión técnica', 'gestion_eventos'),
        ),
        'plantas_piloto': (
            ('Órdenes de producción con revisión técnica', 'gestion_produccion'),
            ('Controles de calidad con revisión técnica', 'gestion_control_calidad'),
        ),
        'centro_experimental': (
            ('Ciclos o ensayos con seguimiento y revisión técnica', 'gestion_ensayos'),
        ),
    }
    pares.extend((etiqueta, valor(clave)) for etiqueta, clave in indicadores.get(base, ()))
    return pares


def datos_automaticos(documento, inicio, fin, contenido=None):
    """Bloques que el sistema aporta a cada apartado, por código de apartado."""
    if documento.exigido.fuente_reporte == 'protocolo':
        from .protocolo_contexto import bloques_automaticos
        return bloques_automaticos(documento, contenido)
    unidad = documento.unidad
    contenido = contenido or {}
    tipo = documento.exigido.fuente_reporte
    bloques = {'general': [{'tipo': 'pares', 'titulo': 'Datos de la ficha institucional',
                            'pares': _pares_generales(documento, inicio, fin)}]}
    if tipo == 'planificacion':
        bloques['mejora_previa'] = _bloques_de_evaluacion_previa(documento)
        if contenido.get('recursos_periodo_version') == 1:
            from .recursos_periodo import bloques_recursos
            bloques['inversion'] = bloques_recursos(documento, inicio, fin, contenido)
        else:
            bloques['inversion'] = [bloque_de_sugerencias(unidad, hasta=fin)]
    if tipo == 'compras':
        if contenido.get('pac_version') == 2:
            from .diagnostico_compras import lectura_diagnostico, bloques_diagnostico
            lectura = lectura_diagnostico(documento, contenido)
            bloques['general'] = [{'tipo': 'pares', 'titulo': 'Unidad solicitante', 'pares': [
                ('Unidad', unidad.nombre),
                ('Tipo de unidad', unidad.nombre_tipologia or (unidad.dependencia or '').replace('_', ' ').title()),
                ('Responsable', _nombre(unidad.administrador)),
                ('Decanato o dependencia', str(unidad.adscrita_a) if unidad.adscrita_a_id else 'Sin adscripción registrada'),
                ('Centro de costo agrupador', contenido.get('centro_costo') or 'Pendiente de confirmar por la dependencia'),
                ('Año de preparación', str(documento.anio)),
                ('Año de las compras', str(documento.anio + 1)),
            ]}]
            if contenido.get('compras_resumen_version') == 1:
                from .sustento_compras import respaldo_compras, bloques_respaldo_compras
                respaldo = respaldo_compras(lectura, contenido)
                bloques['diagnostico_compras'] = bloques_respaldo_compras(respaldo)
                bloques['_respaldo_compras'] = respaldo
            else:
                bloques['diagnostico_compras'] = bloques_diagnostico(lectura, contenido)
            bloques['_diagnostico_compras'] = lectura
            if contenido.get('inversion_gestion_version') == 1:
                from .priorizacion_necesidades import lectura_gestion_inversion, bloques_gestion_inversion
                gestion = lectura_gestion_inversion(documento, contenido)
                bloques['gestion_inversion'] = bloques_gestion_inversion(gestion)
                bloques['_priorizacion_inversion'] = gestion
            return bloques
        bloques['sugerencias'] = [bloque_de_sugerencias(unidad, hasta=date(documento.anio + 1, 12, 31)),
            {'tipo': 'parrafo', 'texto': 'Diagnóstico del inventario consultado al elaborar el documento. '
             'La vida útil y el valor del activo son referencias: la unidad confirma necesidad, diagnóstico, '
             'cantidades, cotizaciones y financiamiento. La propuesta no autoriza gastos ni da de baja equipos.'}]
        bloques['general'][0]['pares'].append(('Año planificado', str(documento.anio + 1)))
        from apps.documentos.presentation.priorizacion_compras import analizar_priorizacion
        prioridad = analizar_priorizacion(documento, contenido)
        bloques['_priorizacion_inversion'] = prioridad
        pares_prioridad = [('Resultado', prioridad['label'])]
        if prioridad['estado'] != 'sin_solicitud':
            pares_prioridad.extend([
                ('Período de referencia', (prioridad.get('periodo') or {}).get('etiqueta', 'Sin antecedente cerrado')),
                ('Resultado operativo acreditado', str(prioridad['porcentaje']) + ' %'
                 if prioridad.get('porcentaje') is not None else 'Sin resultado acreditado'),
                ('Umbral de referencia', str(prioridad['umbral']) + ' %'),
            ])
        pares_prioridad.append(('Alcance', 'La conformidad documental no autoriza financiamiento ni ejecución de compras.'))
        bloques['priorizacion_inversion'] = [
            {'tipo': 'pares', 'titulo': 'Lectura de prioridad de la solicitud', 'pares': pares_prioridad},
            {'tipo': 'parrafo', 'texto': prioridad['explicacion']}]
    if tipo == 'informe':
        if contenido.get('recursos_periodo_version') == 1:
            from .recursos_periodo import bloques_recursos
            bloques['presupuesto'] = bloques_recursos(documento, inicio, fin, contenido)
        else:
            bloques['presupuesto'] = [_bloque_de_lo_planificado(documento)]
    if tipo == 'planificacion':
        responsables = ResponsableUnidad.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre')
        bloques['general'][0]['pares'] = [(k, v) for k, v in bloques['general'][0]['pares'] if k != 'Equipo de la unidad']
        bloques['estructura'] = [{'tipo': 'tabla', 'titulo': 'Equipo de la unidad',
                                  'cabecera': ['Nombre', 'Cargo', 'Responsabilidades'],
                                  'filas': [[r.nombre, r.get_rol_display(),r.descripcion or ''] for r in responsables]}]
        espacios = EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('nombre')
        servicios = FablabService.objects.filter(unidad=unidad).order_by('nombre')
        bloques['alcance'] = [
            {'tipo': 'lista', 'titulo': 'Áreas y espacios de trabajo registrados',
             'items': [f'{e.nombre} · {e.get_tipo_display()}' + (f' · capacidad {e.capacidad}' if e.capacidad else '')
                       for e in espacios]},
            {'tipo': 'lista', 'titulo': 'Servicios y productos registrados',
             'items': [s.nombre for s in servicios]},
        ]
        equipos = equipos_de(unidad).select_related('equipo').prefetch_related('equipo__categorias')
        estados = Counter(equipos.values_list('estado_unidad', flat=True))
        nombres_estado = dict(UnidadEquipo.ESTADO_UNIDAD_CHOICES)
        bloques['diagnostico'] = [{'tipo': 'pares', 'titulo': 'Estado de los equipos en el inventario',
                                   'pares': [(nombres_estado.get(k, k), str(v)) for k, v in sorted(estados.items())]
                                   or [('Equipos registrados', '0')]}]
        por_categoria = Counter(
            equipos.values_list('equipo__categorias__nombre', flat=True)) if equipos.exists() else Counter()
        valor = equipos.aggregate(total=Sum('valor_referencial'))['total'] or Decimal(0)
        software = SoftwareDisponible.objects.filter(unidad=unidad).order_by('nombre')
        insumos = Consumible.objects.filter(unidad=unidad).order_by('nombre')
        # La planificación lleva el resumen del inventario; la lista completa de equipos, software e insumos
        # se consulta y exporta en el Centro de reportes y su revisión física va en el anexo de equipos.
        bloques['inventario'] = [
            {'tipo': 'pares', 'titulo': 'Resumen del inventario', 'pares': [
                ('Equipos registrados', str(equipos.count())),
                ('Valor referencial total (USD)', f'{valor:,.2f}'),
                ('Software y licencias', f'{software.count()} programas · '
                 f'{software.aggregate(t=Sum("licencias_totales"))["t"] or 0} licencias'),
                ('Insumos y materiales en catálogo', str(insumos.count())),
                ('Espacios reservables', str(espacios.count())),
            ]},
            {'tipo': 'tabla', 'titulo': 'Equipos por categoría', 'cabecera': ['Categoría', 'Equipos'],
             'filas': [[k or 'Sin categoría', str(v)] for k, v in sorted(por_categoria.items(), key=lambda x: str(x[0]))]},
            {'tipo': 'parrafo', 'texto': 'La lista completa de equipos, software e insumos se consulta y se exporta '
                                         'en el Centro de reportes de la unidad.'},
        ]
        nuevo = bool((contenido.get('actividades') or {}).get('metas_estandar'))
        bloques['cronograma'] = [_bloque_cronograma(unidad, contenido, inicio, fin)]
        if nuevo:
            cronograma = (contenido.get('actividades') or {}).get('cronograma_auto') or {}
            bloques['cronograma'].append(dict(tipo='pares', titulo='Ventana preventiva general del semestre', pares=[
                ('Programación general', (cronograma.get('origenes') or {}).get('MANTENIMIENTO', 'Por programar.')),
                ('Correctivos e incidencias', 'Se registran en sus órdenes e informes propios de mantenimiento; '
                    'no son una obligación mensual añadida a la planificación inicial.')]))
        bloques['cronograma'].append(_bloque_mantenimientos(unidad, inicio, fin, solo_programados=nuevo))
    elif tipo == 'informe':
        registros = registros_del_periodo(unidad, inicio, fin)
        tipos_usuario = dict(_tipos_usuario())
        bloques['uso'] = [
            {'tipo': 'pares', 'titulo': 'Actividad registrada en la plataforma',
             'pares': _pares_uso_informe(unidad, registros)},
            {'tipo': 'tabla', 'titulo': 'Sesiones por tipo de usuario', 'cabecera': ['Tipo de usuario', 'Sesiones'],
             'filas': [[tipos_usuario.get(k, 'Sin tipo' if k == 'sin_tipo' else k), str(v)]
                       for k, v in sorted(registros['usuarios_por_tipo'].items(), key=lambda x: -x[1])]},
        ]
        # El enlace abre la evidencia exacta; una marca manual no certifica sus indicadores. Los anexos llevan
        # el mismo número que la columna «Anexo» del cumplimiento.
        from apps.documentos.presentation.anexos_evidencia import anexos_numerados
        base_url = settings.SITE_URL.rstrip('/')
        numerados = anexos_numerados(documento)
        items = [{'texto': f'Anexo {numero}. {d.nombre_documental}',
                  **({'url': base_url + reverse('recurso_unidad', args=[d.recurso_id])} if d.recurso_id else {})}
                 for numero, d in numerados]
        presentados = {d.pk for _, d in numerados}
        items.extend({'texto': d.nombre_documental,
                      'url': base_url + reverse('recurso_unidad', args=[d.recurso_id])}
                     for d in DocumentoExpediente.objects.filter(
                         unidad=unidad, anio=documento.anio, recurso__isnull=False, exigido__activo=True,
                         exigido__codigo='PLANIFICACION', corte=documento.corte,
                     ).exclude(pk__in=presentados).select_related('exigido'))
        bloques['anexos'] = [{'tipo': 'lista', 'titulo': 'Anexos del informe y planificación del período · abrir documento',
                              'items': items}]
        bloques['_registros'] = registros
        if documento.pk:
            bloques['mejora'] = _bloques_de_mejora_formal(documento)
    return bloques


def _bloques_de_mejora_formal(documento):
    """Lo que antes iba en el anexo «Acciones de mejora» (documentos.0025): las acciones que dispuso la
    Dirección con su seguimiento y los incumplimientos del expediente del período, sin transcribirlos."""
    from apps.documentos.models.mejora import AccionMejora

    bloques = []
    acciones = AccionMejora.objects.filter(
        informe__unidad=documento.unidad, informe__anio=documento.anio,
    ).filter(Q(informe__corte=documento.corte) | Q(informe__corte='')).select_related(
        'responsable', 'informe').prefetch_related('seguimientos__creado_por')
    formales, avances = [], []
    for accion in acciones:
        formales.append([str(accion.pk), accion.descripcion, str(accion.responsable), f'{accion.vence_el:%d/%m/%Y}',
                         'Cerrada' if accion.cerrada_en else 'Pendiente'])
        avances.extend([str(accion.pk), f'{timezone.localtime(avance.creado_en):%d/%m/%Y}', str(avance.creado_por),
                        avance.detalle, 'Sí' if avance.cierre else 'No'] for avance in accion.seguimientos.all())
    if formales:
        bloques.append({'tipo': 'tabla', 'titulo': 'Acciones dispuestas por la Dirección',
                        'cabecera': ['N.º', 'Acción', 'Responsable', 'Plazo', 'Estado'], 'filas': formales,
                        'anchos_relativos': [.07, .45, .20, .13, .15]})
    if avances:
        bloques.append({'tipo': 'tabla', 'titulo': 'Seguimiento de esas acciones',
                        'cabecera': ['Acción', 'Fecha', 'Autor', 'Avance y evidencia', 'Cierre verificado'],
                        'filas': avances, 'anchos_relativos': [.09, .13, .18, .44, .16]})
    incumplidos = incumplimientos_del_periodo(documento)
    if incumplidos:
        bloques.append({'tipo': 'tabla', 'titulo': 'Entregas del expediente fuera de plazo u observadas',
                        'cabecera': ['Documento', 'Período', 'Estado', 'Venció', 'Atraso', 'Motivo'],
                        'filas': incumplidos, 'anchos_relativos': [.24, .12, .14, .12, .08, .30]})
    return bloques


def _bloque_de_lo_planificado(documento):
    """Lo que la planificación del período previó comprar, para rendir cuentas en el informe."""
    plan = planificacion_del_periodo(documento)
    filas = analizar_presupuesto('planificacion', plan.contenido)['filas'] if plan is not None else []
    if not filas:
        return {'tipo': 'vacio', 'titulo': 'Actividades previstas en la planificación',
                'texto': 'La planificación del período no previó compras.' if plan is not None
                else 'El período no tiene planificación redactada en el sistema.'}
    cuerpo, total = [], Decimal(0)
    for fila in filas:
        subtotal = _decimal(fila.get('cantidad') or 0) * _decimal(fila.get('costo_unitario') or 0)
        total += subtotal
        cuerpo.append([_etiqueta(CATEGORIAS_INVERSION, fila.get('categoria', '')), fila.get('item', '') or '—',
                       str(fila.get('cantidad', '') or '—'), _etiqueta(PRIORIDADES, fila.get('prioridad', '')),
                       f'{subtotal:,.2f}'])
    cuerpo.append(['Total planificado', '', '', '', f'{total:,.2f}'])
    return {'tipo': 'tabla', 'titulo': 'Actividades previstas en la planificación',
            'cabecera': ['Categoría', 'Ítem', 'Cantidad', 'Prioridad', 'Total (USD)'], 'filas': cuerpo}


def _bloques_de_evaluacion_previa(documento):
    """La evaluación de la Dirección del período anterior, para que la planificación la responda."""
    from apps.documentos.presentation.expediente import evaluaciones_del_periodo_anterior

    previas = evaluaciones_del_periodo_anterior(documento.unidad, documento.anio, documento.corte or 'A')
    if not previas:
        return [{'tipo': 'vacio', 'texto': 'La Dirección no dejó evaluación del período anterior.'}]
    bloques = []
    from .conformidad_lectura import completar_conformidades, lectura_conformidad
    completar_conformidades(previas)
    for previa in previas:
        conformidad = lectura_conformidad(previa)
        pares = ([('Conformidad documental', conformidad['etiqueta']),
                  ('Antecedente', 'La revisión histórica se conserva; no es una nueva calificación del plan.')]
                 if conformidad else [('Cumplimiento evaluado', f'{previa.evaluacion} %')])
        for etiqueta, texto in (('Conclusión', previa.evaluacion_observacion),
                                ('Fortalezas', previa.evaluacion_fortalezas),
                                ('Debilidades', previa.evaluacion_debilidades),
                                ('Recomendaciones', previa.evaluacion_recomendaciones)):
            if texto:
                pares.append((etiqueta, texto))
        bloques.append({'tipo': 'pares', 'titulo': f'{previa.nombre_documental} · {previa.etiqueta_corte}',
                        'pares': pares})
    return bloques


def _tipos_usuario():
    from apps.core.presentation.catalogos import tipos_usuario
    try:
        return tuple(tipos_usuario())
    except Exception:  # pragma: no cover - identidad sin catálogo
        return ()


def filas_del_plan(unidad, contenido, inicio, fin):
    """Actividades del plan (catálogo + propias) con lo marcado; para el editor y el documento.

    Una obligatoria sin meses escritos toma los que el sistema prevé, de modo
    que el cronograma se mantiene al día con los planes de mantenimiento y las
    prácticas ya programadas aunque el plan se haya guardado antes.
    """
    from apps.documentos.presentation.evaluacion_cierre import ANEXOS_METAS
    from apps.documentos.presentation.expediente_catalogo import CATALOGO
    from apps.documentos.presentation.politica_metas_unidades import capacidad_archivada, capacidad_de
    plan = contenido.get('actividades') or {}
    capacidad = capacidad_archivada(plan) or capacidad_de(unidad, inicio, fin)
    catalogo = plan.get('catalogo') or {}
    cronograma = plan.get('cronograma_auto') or {}
    automatico = isinstance(cronograma, dict) and cronograma.get('version') == 1
    previstos = None
    filas = []
    for actividad in actividades_para(unidad, version=plan.get('minimos_catalogo', 3 if not plan else 0),
                                      funciones=contenido.get('sectores'), capacidad=capacidad):
        marcado = catalogo.get(actividad.codigo) or {}
        version_minimos = plan.get('minimos_catalogo', 3 if not plan else 0)
        por_tipo = bool(version_minimos and obligatoria_por_tipo(actividad, version=version_minimos))
        solo_anexo = version_minimos >= 2 and actividad.codigo in ANEXOS_AUTOMATICOS
        requerida = actividad.obligatoria or por_tipo
        meses = list(marcado.get('meses') or [])
        if automatico:
            meses = list((cronograma.get('meses_por_actividad') or {}).get(actividad.codigo, meses))
            if not (requerida or marcado.get('aplica')):
                meses = []
        elif requerida and not meses:
            if previstos is None:
                previstos = meses_por_defecto(unidad, inicio, fin, historico=True)
            meses = list(previstos.get(actividad.codigo, []))
            if not meses:
                meses = [m for m, _ in meses_del_tramo(inicio, fin)]
        obligatoria = requerida or bool(marcado.get('obligatoria', marcado.get('aplica', False)))
        anexos = [d[1] for d in CATALOGO if actividad.codigo in ANEXOS_METAS.get(d[0], ())]
        from types import SimpleNamespace
        from .perfil_unidades import nombre_para
        reportes = [nombre_para(SimpleNamespace(codigo=d[0], nombre=d[1]), unidad)
                    for d in CATALOGO if actividad.codigo in ANEXOS_METAS.get(d[0], ())]
        politica = plan.get('metas_estandar') or {}
        politica = politica if isinstance(politica, dict) else {}
        origenes = politica.get('origenes') or {}
        origenes = origenes if isinstance(origenes, dict) else {}
        filas.append({
            'codigo': actividad.codigo, 'nombre': actividad.nombre, 'indicador': actividad.indicador,
            # Un registro sin meta conserva su propio nombre: el anexo que lo trae ya nombra a la meta que respalda.
            'nombre_reporte': reportes[0] if reportes and not solo_anexo else actividad.nombre,
            'meta_origen': origenes.get(actividad.codigo, ''),
            'minimo': actividad.minimo, 'contador': actividad.contador, 'propia': False,
            'obligatoria': obligatoria, 'institucional': actividad.obligatoria, 'por_tipo': por_tipo,
            'solo_anexo': solo_anexo,
            'politica_metas': version_minimos,
            'segun_programacion': actividad.segun_programacion,
            'requisito': requerida, 'definida': bool(marcado) or requerida or actividad.segun_programacion, 'anexos': anexos,
            'aplica': requerida or bool(marcado.get('aplica')),
            # Una obligatoria sin meta escrita responde al mínimo institucional.
            'meta': marcado.get('meta') or (actividad.minimo if requerida else ''),
            'meses': meses, 'responsable': marcado.get('responsable', ''),
            'cronograma_auto': automatico,
            'cronograma_origen': (cronograma.get('origenes') or {}).get(actividad.codigo, ''),
            'sin_programacion_exigible': bool(automatico and actividad.codigo == 'MANTENIMIENTO'
                                             and (not cronograma.get('mantenimiento_exigible')
                                                  or cronograma.get('mantenimiento_meses_por_equipo'))),
        })
    for indice, otra in enumerate(plan.get('otras') or []):
        filas.append({
            'codigo': f'otra-{indice}', 'nombre': otra.get('nombre', ''), 'indicador': otra.get('indicador', ''),
            'minimo': '', 'contador': '', 'propia': True, 'aplica': True, 'obligatoria': True,
            'institucional': False, 'definida': True, 'meta': otra.get('meta', ''),
            'meses': list(otra.get('meses') or []), 'responsable': otra.get('responsable', ''), 'indice': indice,
        })
    presupuesto = contenido.get('presupuesto_uso')
    if (isinstance(presupuesto, dict) and presupuesto.get('version') == 1
            and unidad.codigo_base != 'observatorios'):
        try:
            meta_uso = Decimal(str(presupuesto.get('horas_comprometidas', '')))
            if not meta_uso.is_finite() or meta_uso < 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            meta_uso = Decimal(0)
        filas.append(dict(codigo='USO-EFECTIVO', nombre='Uso efectivo frente a las horas comprometidas',
            indicador='Horas de actividad realizadas y respaldadas', minimo='Según programación justificada',
            contador='horas_uso_efectivo', propia=False, obligatoria=meta_uso > 0,
            institucional=False, por_tipo=False, solo_anexo=False, politica_metas=3,
            segun_programacion=True, requisito=False, definida=meta_uso > 0, anexos=['Registro de uso'],
            aplica=meta_uso > 0, meta=format(meta_uso, 'f') if meta_uso > 0 else '',
            meses=[int(m) for m in (presupuesto.get('horas_por_mes') or {}) if str(m).isdigit() and 1 <= int(m) <= 12],
            responsable=contenido.get('firma_nombre', 'Coordinación de la unidad')))
    if plan.get('metas_estandar'):
        filas.sort(key=lambda f: ORDEN_PLAN.index(f['codigo']) if f['codigo'] in ORDEN_PLAN else len(ORDEN_PLAN))
    return filas


def _bloque_cronograma(unidad, contenido, inicio, fin):
    meses = meses_del_tramo(inicio, fin)
    nuevo = (contenido.get('actividades') or {}).get('metas_estandar')
    filas = [((f.get('nombre_reporte') or f['nombre']) if nuevo else f['nombre'], [m in f['meses'] for m, _ in meses])
             for f in filas_del_plan(unidad, contenido, inicio, fin) if f['aplica']]
    return {'tipo': 'cronograma', 'titulo': 'Meses previstos por actividad', 'meses': [n for _, n in meses],
            'filas': filas}


def problemas_cronograma(unidad, contenido, inicio, fin):
    """Faltantes objetivos de fechas; las asignaciones operativas viven en su módulo."""
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    if not es_unidad_auditable(unidad):
        return []
    pendientes = []
    for fila in filas_del_plan(unidad, contenido, inicio, fin):
        if not fila['aplica'] or fila.get('solo_anexo'):
            continue
        if fila.get('meses') or fila.get('sin_programacion_exigible'):
            continue
        calendario_pendiente = bool(fila.get('cronograma_auto') and fila['codigo'] in ACTIVIDADES_DOCENTES)
        mensaje = (fila.get('cronograma_origen') or 'Calendario académico pendiente de configurar.') if calendario_pendiente else (
            'Pendiente de programar: registra las fechas de mantenimiento de los equipos exigibles.'
            if fila['codigo'] == 'MANTENIMIENTO' else 'Faltan meses de ejecución.')
        pendientes.append(dict(regla='calendario_docente_pendiente' if calendario_pendiente else 'actividad_incompleta',
            mensaje=f"{fila['nombre']}: {mensaje}", severidad='revision' if calendario_pendiente else 'bloqueo'))
    return pendientes


def pendientes_actividades(unidad, contenido, inicio, fin):
    return [p['mensaje'] for p in problemas_cronograma(unidad, contenido, inicio, fin)]


def planificacion_del_periodo(documento):
    """No traslada compromisos entre un semestre de gestión y un tramo legado."""
    from .expediente import tramo_del_documento

    tramo = tramo_del_documento(documento)
    candidatos = DocumentoElaborado.objects.filter(
        documento__unidad=documento.unidad, documento__anio=documento.anio, documento__corte=documento.corte,
        documento__exigido__fuente_reporte='planificacion',
    ).select_related('documento__exigido', 'documento__unidad')
    return next((r for r in candidatos if r.documento.marco_periodo == documento.marco_periodo
                 and tramo_del_documento(r.documento) == tramo), None)


NOMBRES_VEREDICTO = {'cumple': 'Cumple', 'no_cumple': 'No cumple', 'sin_medicion': 'Sin medición automática'}


def veredicto_de_meta(fila, registros):
    """El resumen usa la misma medición verificable que el cierre y su PDF."""
    from apps.documentos.presentation.evaluacion_cierre import medir_meta

    lectura = medir_meta({'nombre': fila.get('codigo', ''), 'contador': 'registrado', **fila}, registros)
    if lectura['pendiente']:
        return 'sin_medicion'
    return 'cumple' if lectura['porcentaje'] == 100 else 'no_cumple'


def filas_de_cumplimiento(documento, contenido, inicio, fin, registros=None):
    """Cada actividad del plan con meta, registrado por el sistema, reportado por la unidad y veredicto."""
    plan = planificacion_del_periodo(documento)
    registros = registros if registros is not None else registros_del_periodo(documento.unidad, inicio, fin)
    reportado = contenido.get('cumplimiento') or {}
    filas, todas = [], []
    if plan is not None:
        presupuesto = plan.contenido.get('presupuesto_uso')
        if presupuesto and documento.unidad.codigo_base != 'observatorios':
            from apps.recursos.presentation.seguimiento_uso import seguimiento_uso_unidad
            seguimiento = seguimiento_uso_unidad(documento.unidad, inicio, fin, presupuesto=presupuesto)
            registros['seguimiento_uso'] = seguimiento
            registros.setdefault('fuentes_gestion', {})['USO-EFECTIVO'] = [seguimiento['semestre']['fuentes_medicion']]
            registros['horas_uso_efectivo'] = (None if seguimiento['semestre'].get('pending')
                else seguimiento['semestre']['occupied_hours'])
        for fila in filas_del_plan(documento.unidad, plan.contenido, inicio, fin):
            registrado = registros.get(fila['contador']) if fila['contador'] else None
            propio = reportado.get(fila['codigo']) or {}
            fila = {
                **fila,
                'registrado': registrado,
                'realizado': propio.get('realizado', '' if registrado is None else str(registrado)),
                'observacion': propio.get('observacion', ''),
            }
            fila['veredicto'] = veredicto_de_meta(fila, registros)
            fila['nombre_veredicto'] = NOMBRES_VEREDICTO[fila['veredicto']]
            todas.append(fila)
            if fila['aplica']:
                filas.append(fila)
    return {'hay_plan': plan is not None, 'filas': filas, 'todas': todas, 'registros': registros}


def metas_del_periodo(documento, inicio=None, fin=None):
    """Las metas del período del documento con su veredicto, para el expediente y la evaluación."""
    from apps.documentos.presentation.expediente import tramo_del_documento

    if inicio is None or fin is None:
        inicio, fin = tramo_del_documento(documento)
    redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first()
    datos = filas_de_cumplimiento(documento, redaccion.contenido if redaccion else {}, inicio, fin)
    filas = datos['filas']
    medibles = [f for f in filas if f['veredicto'] != 'sin_medicion']
    return {
        'hay_plan': datos['hay_plan'],
        'filas': filas,
        'todas': datos['todas'],
        'medibles': len(medibles),
        'cumplidas': sum(1 for f in medibles if f['veredicto'] == 'cumple'),
        'incumplidas': [f for f in medibles if f['veredicto'] == 'no_cumple'],
        'registros': datos['registros'],
    }


# -- componer el documento (vista previa y PDF) ---------------------------------

def _etiqueta(opciones, valor):
    return dict(opciones).get(valor, valor)


def componer(documento, contenido, inicio, fin):
    """Estructura única del documento: apartados numerados con bloques listos para HTML o PDF."""
    tipo = documento.exigido.fuente_reporte
    if tipo == 'protocolo':
        from .protocolo_contexto import completar_contenido
        contenido = completar_contenido(documento, contenido)
    automaticos = datos_automaticos(documento, inicio, fin, contenido)
    secciones = []
    for numero, seccion in enumerate(secciones_de(tipo, documento.unidad, contenido), start=1):
        bloques = list(automaticos.get(seccion.automatico, [])) if seccion.automatico else []
        for campo in seccion.campos:
            bloques.extend(_bloques_del_campo(campo, contenido.get(campo.clave), documento, contenido, inicio, fin,
                                              automaticos.get('_registros')))
        if seccion.codigo == 'firmas':
            pares = [(rol, f'{nombre} · {cargo}' if cargo else nombre) for rol, nombre, cargo in (
                ('Elaborado por', contenido.get('firma_nombre', ''), contenido.get('firma_cargo', '')),
                ('Revisado por', contenido.get('revisa_nombre', ''), contenido.get('revisa_cargo', '')),
            ) if nombre]
            bloques.append({'tipo': 'pares', 'titulo': 'Quienes firman el documento', 'pares': pares} if pares
                           else {'tipo': 'vacio', 'texto': 'Falta indicar quién elabora el documento.'})
        if not bloques:
            bloques.append({'tipo': 'vacio', 'texto': 'Sin información registrada.'})
        secciones.append({'numero': numero, 'codigo': seccion.codigo, 'titulo': seccion.titulo, 'bloques': bloques})
    if (tipo == 'compras' and contenido.get('pac_version') == 2
            and contenido.get('estado_equipos_informe_version') == 1):
        from .sustento_compras import resumen_estado_equipos, bloques_estado_equipos
        # Orden propio del informe: el editor conserva sus apartados y pestañas.
        # La versión de presentación mantiene íntegra la huella de PDF anteriores.
        estado = resumen_estado_equipos(automaticos.get('_diagnostico_compras') or {})
        posicion = next((i for i, s in enumerate(secciones) if s['codigo'] == 'compras'), len(secciones))
        secciones.insert(posicion, dict(numero=0, codigo='estado_equipos',
            titulo='Estado de los equipos existentes', bloques=bloques_estado_equipos(estado)))
        for n, s in enumerate(secciones, 1):
            s['numero'] = n
    if (tipo == 'informe' and getattr(documento, 'marco_periodo', '') == 'gestion_v1'
            and documento.unidad.codigo_base != 'observatorios'):
        from apps.gestion_unidades.presentation.reportes_capacidad import reporte_capacidad
        uso = reporte_capacidad(documento.unidad, inicio, fin)
        # Dos cuadros legibles en A4 vertical, con todos los datos del reporte.
        columnas = ((0, 1, 2, 8, 9), (0, 3, 4, 5, 6, 7, 10))
        titulos = ('Horas disponibles, ejecución y compromiso mensual',
                   'Capacidad, aprovechamiento y calidad de la medición')
        bloques_uso = [{'tipo': 'tabla', 'titulo': titulo,
            'cabecera': [uso['headers'][i] for i in indices],
            'filas': [[fila[i] for i in indices] for fila in uso['rows']]}
            for titulo, indices in zip(titulos, columnas)]
        bloques_uso.extend({'tipo': 'parrafo', 'texto': nota} for nota in uso['notes'])
        posicion = next((i for i, s in enumerate(secciones) if s['codigo'] == 'firmas'), len(secciones))
        secciones.insert(posicion, dict(numero=0, codigo='aprovechamiento',
            titulo='Capacidad y aprovechamiento efectivo del semestre', bloques=bloques_uso))
        for n, s in enumerate(secciones, 1):
            s['numero'] = n
    return {
        'tipo': tipo,
        **({'pac_datos': deepcopy(contenido)} if tipo == 'compras' and contenido.get('pac_version') in (1, 2) else {}),
        'titulo': (NOMBRES_TIPO[tipo] if tipo == 'compras' and contenido.get('pac_version') == 2 else
                   documento.nombre_documental if es_unidad_auditable(documento.unidad) else NOMBRES_TIPO[tipo]),
        'codigo_formato': referencia_interna(documento) if es_unidad_auditable(documento.unidad) else CODIGOS_FORMATO[tipo],
        'codigo_etiqueta': 'Referencia interna' if es_unidad_auditable(documento.unidad) else 'Código',
        'documento': documento,
        'unidad': documento.unidad,
        'periodo': ('Documento permanente' if tipo == 'protocolo' else
                    f'Año de compras {documento.anio + 1} · preparación {documento.anio}'
                    if tipo == 'compras' and contenido.get('pac_version') == 2 else documento.etiqueta_corte),
        'version': documento.version + 1,
        'tramo': (inicio, fin),
        'secciones': secciones,
        'firmas': [
            ('Elaborado por', contenido.get('firma_nombre', ''), contenido.get('firma_cargo', '')),
            ('Revisado por', contenido.get('revisa_nombre', ''), contenido.get('revisa_cargo', '')),
        ],
    }


def _bloques_del_campo(campo, valor, documento, contenido, inicio, fin, registros):
    if campo.clave == 'revision_recursos':
        return []
    if documento.exigido.fuente_reporte == 'protocolo' and campo.clave == 'revision_propuestas':
        return []  # La confirmación de edición no forma parte del texto formal.
    if campo.tipo == 'firmas' or campo.clave in ('firma_nombre', 'firma_cargo', 'revisa_nombre', 'revisa_cargo'):
        return []
    if campo.tipo == 'presupuesto_uso':
        from .presupuesto_uso import datos_presupuesto
        dato = datos_presupuesto(valor, inicio, fin)
        bloques = [{'tipo': 'tabla', 'titulo': 'Programación de horas de actividad efectiva',
            'cabecera': ['Mes', 'Horas comprometidas'], 'filas': [
                [m['nombre'], m['horas'] or 'Sin programación declarada'] for m in dato['meses']]},
            {'tipo': 'pares', 'titulo': 'Compromiso de uso', 'pares': [('Total de horas', dato['total'] or 'Sin definir'),
                ('Medición', 'Atenciones efectivas con horario y asistencia reales. Las reservas no ejecutadas no suman.')]}]
        if dato['justificacion']:
            bloques.append({'tipo': 'rico', 'titulo': 'Fundamento de la programación',
                'html': dato['justificacion'], 'bloques': bloques_de_html(dato['justificacion'])})
        return bloques
    if campo.tipo == 'rico':
        html = html_del_campo(campo, valor)
        if esta_vacio(html):
            if campo.clave in TEXTOS_VACIOS:
                return [{'tipo': 'vacio', 'titulo': campo.etiqueta, 'texto': TEXTOS_VACIOS[campo.clave]}]
            return []
        return [{'tipo': 'rico', 'titulo': campo.etiqueta, 'html': html, 'bloques': bloques_de_html(html)}]
    if campo.tipo == 'texto':
        texto = str(valor or '').strip()
        return [{'tipo': 'parrafo', 'titulo': campo.etiqueta, 'texto': texto}] if texto else []
    if campo.tipo == 'opcion':
        return [{'tipo': 'parrafo', 'titulo': campo.etiqueta, 'texto': _etiqueta(campo.opciones, valor)}] if valor else []
    if campo.tipo == 'marcas':
        items = [_etiqueta(campo.opciones, v) for v in (valor or [])]
        return [{'tipo': 'lista', 'titulo': campo.etiqueta, 'items': items}] if items else []
    if campo.tipo == 'tabla':
        if campo.clave == 'compras' and contenido.get('pac_version') in (1, 2):
            from .pac_universitario import bloques_pac
            return bloques_pac(contenido)
        if documento.exigido.fuente_reporte == 'protocolo' and not valor and not campo.requerido:
            return []
        if documento.exigido.fuente_reporte == 'protocolo' and campo.clave in ('riesgos_protocolo', 'emergencias_protocolo'):
            activas = [fila for fila in valor or [] if fila.get('aplica') != 'no']
            omitidas = [fila for fila in valor or [] if fila.get('aplica') == 'no']
            campo_pdf = replace(campo, columnas=tuple(c for c in campo.columnas if c[0] != 'aplica'))
            bloques = [_bloque_tabla(campo_pdf, activas)] if activas else []
            if bloques:
                bloques[0]['anchos_relativos'] = ([.19, .21, .25, .15, .20] if campo.clave == 'riesgos_protocolo'
                                                  else [.22, .36, .18, .24])
            if omitidas:
                bloques.append(dict(tipo='tabla', titulo='Actividades no aplicables',
                    cabecera=['Actividad o situación', 'Justificación'], filas=[
                        [f.get('actividad') or f.get('situacion'), f.get('control') or f.get('respuesta')] for f in omitidas]))
            return bloques
        return [_bloque_tabla(campo, valor or [])]
    if campo.tipo == 'actividades':
        filas = [f for f in filas_del_plan(documento.unidad, contenido, inicio, fin)
                 if f['aplica'] or f.get('anexos')]
        if not filas:
            return [{'tipo': 'vacio', 'texto': 'La unidad no marcó actividades para el período.'}]
        cronograma = (contenido.get('actividades') or {}).get('cronograma_auto') or {}
        nuevo_plan = (getattr(documento.exigido, 'fuente_reporte', '') == 'planificacion'
                      and isinstance(cronograma, dict) and cronograma.get('version') == 1)
        cabecera = ['Actividad', 'Exigencia', 'Indicador', 'Mínimo institucional', 'Meta del período']
        cuerpo = [[f['nombre'], ('Registro del período, sin meta' if f.get('solo_anexo') else
                              'No aplica' if not f['aplica'] else
                              'Obligatoria institucional' if f.get('institucional') else
                              'Obligatoria según tipo de unidad' if f.get('por_tipo') else
                              'Obligatoria del período' if f.get('obligatoria') else 'Opcional'),
                   f['indicador'], f['minimo'] or '—', f['meta'] or '—'] for f in filas]
        if (contenido.get('actividades') or {}).get('metas_estandar'):
            cabecera = ['Documento o actividad', 'Exigencia', 'Indicador', 'Meta del período']
            cuerpo = [[f.get('nombre_reporte') or f['nombre'], celdas[1], celdas[2], celdas[4]]
                      for f, celdas in zip(filas, cuerpo)]
        if not nuevo_plan:
            cabecera.append('A cargo de')
            for celdas, fila in zip(cuerpo, filas):
                celdas.append(fila['responsable'] or '—')
        bloques = [{'tipo': 'tabla', 'titulo': 'Actividades comprometidas',
                    'cabecera': cabecera, 'filas': cuerpo}]
        estandar = (contenido.get('actividades') or {}).get('metas_estandar') or {}
        estandar = estandar if isinstance(estandar, dict) else {}
        if estandar:
            carga = estandar.get('carga_docente') or {}
            bloques.append(dict(tipo='pares', titulo='Origen de las metas del semestre', pares=[
                ('Administración de las reglas', 'Dirección. La unidad no modifica los números del catálogo.'),
                ('Carga docente', carga.get('formula', 'No corresponde a la función de esta unidad.')),
                ('Horas de ocupación académica previstas' if estandar.get('version') == 2 else 'Horas docentes previstas',
                    carga.get('horas_requeridas', '—')),
                ('Horas disponibles', carga.get('horas_disponibles', '—')),
                ('Conservación', 'Estas metas y sus fuentes se conservan con esta versión del plan. '
                    'Las limitaciones de carga o capacidad requieren revisión; no se acredita ejecución al planificar.')]))
            if estandar.get('version') == 2 and carga.get('asignaturas'):
                bloques.append(dict(tipo='tabla', titulo='Carga programada por asignatura o actividad',
                    cabecera=['Asignatura o actividad', 'Sesiones', 'Horas de sesiones', 'Desde', 'Hasta'],
                    filas=[[f"{c.get('codigo', '')} {c['nombre']}".strip(), str(c['sesiones']), c['horas'],
                            c['desde'], c['hasta']] for c in carga['asignaturas']]))
        return bloques
    if campo.tipo == 'cumplimiento':
        datos = filas_de_cumplimiento(documento, contenido, inicio, fin, registros)
        if not datos['hay_plan']:
            return [{'tipo': 'vacio', 'texto': 'El período no tiene planificación semestral redactada en el sistema; '
                                               'el cumplimiento no puede compararse con un plan.'}]
        if not datos['filas']:
            return [{'tipo': 'vacio', 'texto': 'La planificación del período no comprometió actividades.'}]
        filas = []
        detalles = []
        from apps.documentos.presentation.anexos_evidencia import anexo_de_cada_meta, cifra, con_respaldo
        from apps.documentos.presentation.evaluacion_cierre import evaluar_meta
        anexos = anexo_de_cada_meta(documento)
        for f in datos['filas']:
            medido = evaluar_meta(f, registros)
            porcentaje = f"{cifra(medido['porcentaje'])} %" if medido['porcentaje'] is not None else '—'
            anexo = anexos.get(f['codigo'], '—')
            filas.append([f['nombre'], f['meta'] or f['minimo'] or '—', cifra(f['registrado']),
                          con_respaldo(f['codigo'], medido, registros), porcentaje, medido['estado'], anexo])
            if medido['estado'] == 'Cumple':
                continue
            detalle = (medido['motivo'] or 'Sin evidencia registrada en el período.').strip()
            reportado = str(f.get('realizado') or '').strip()
            if reportado and reportado != str(f.get('registrado') if f.get('registrado') is not None else ''):
                detalle += f' La unidad reporta {reportado}.'
            if f['observacion']:
                detalle += ' Observación de la unidad: ' + str(f['observacion'])
            if anexo != '—':
                detalle += f' Detalle en el {anexo.lower()}.'
            detalles.append([f['nombre'], detalle])
        medibles = [evaluar_meta(f, registros) for f in datos['filas'] if f.get('obligatoria', True)]
        cumplidas = sum(f['porcentaje'] == 100 for f in medibles)
        bloques = [{'tipo': 'parrafo', 'titulo': 'Cómo se lee el cumplimiento',
                 'texto': (f'De {len(medibles)} metas obligatorias, la unidad cumple {cumplidas}. «Registrado» es lo '
                           'que la plataforma tiene del período; «Con respaldo» es lo que cumple todos los requisitos '
                           'de la meta y es lo único que cuenta para la nota. El avance parcial se acredita en '
                           'proporción, hasta 100 %; sin evidencia se acredita 0 %. Lo que la unidad reporta no '
                           'reemplaza los registros.')},
                {'tipo': 'tabla', 'titulo': 'Planificado frente a realizado',
                 'cabecera': ['Meta', 'Comprometido', 'Registrado', 'Con respaldo', 'Avance', 'Estado', 'Anexo'],
                 'filas': filas, 'anchos_relativos': [.25, .15, .13, .12, .09, .14, .12]}]
        if detalles:
            bloques.append({'tipo': 'tabla', 'titulo': 'Qué falta para cumplir',
                            'cabecera': ['Meta', 'Qué falta'], 'filas': detalles,
                            'anchos_relativos': [.32, .68]})
        return bloques
    return []


TEXTOS_VACIOS = {
    'dificultades': 'La unidad no reporta dificultades en el período.',
    'politicas': 'La unidad no declara políticas adicionales a la normativa institucional.',
    'necesidades_siguiente': 'La unidad no proyecta necesidades adicionales.',
}


def _bloque_tabla(campo, filas):
    if campo.clave in ('inversion', 'compras'):
        tipo = 'planificacion' if campo.clave == 'inversion' else 'compras'
        filas = analizar_presupuesto(tipo, {campo.clave: filas})['filas']
    if not filas:
        texto = {'inversion': 'Sin adquisiciones registradas para el período.',
                 'compras': 'Sin adquisiciones registradas para el año siguiente.',
                 'ejecucion_presupuestal': 'La unidad no reporta ejecución presupuestal.',
                 'acciones': 'La unidad no registra acciones de mejora en el período.'}.get(campo.clave, 'Sin registros.')
        return {'tipo': 'vacio', 'titulo': campo.etiqueta, 'texto': texto}
    cabecera = [etq for _c, etq, *_ in campo.columnas]
    cuerpo, total = [], Decimal(0)
    for fila in filas:
        celdas = []
        for col, _etq, tipo_col, opciones in campo.columnas:
            valor = fila.get(col, '')
            celdas.append(_etiqueta(opciones, valor) if tipo_col == 'opcion' else
                          str(valor if valor is not None and valor != '' else '—'))
        if campo.clave in ('inversion', 'compras'):
            subtotal = _decimal(fila.get('cantidad') or 0) * _decimal(fila.get('costo_unitario') or 0)
            total += subtotal
            celdas.append(f'{subtotal:,.2f}')
        cuerpo.append(celdas)
    if campo.clave in ('inversion', 'compras'):
        cabecera.append('Total (USD)')
        cuerpo.append(['Total proyectado'] + [''] * (len(cabecera) - 2) + [f'{total:,.2f}'])
    return {'tipo': 'tabla', 'titulo': campo.etiqueta, 'cabecera': cabecera, 'filas': cuerpo}


# -- generar ---------------------------------------------------------------------

def pdf_del_documento(documento, redaccion, inicio, fin, estricto=True):
    """Bytes del PDF del documento redactado; si es estricto exige que no falte nada obligatorio."""
    from apps.documentos.presentation.expediente_pdf import render_documento_pdf

    tipo = documento.exigido.fuente_reporte
    if tipo == 'protocolo':
        from .protocolo_contexto import completar_contenido
        contenido_pdf = completar_contenido(documento, redaccion.contenido)
    else:
        contenido_pdf = redaccion.contenido
    if estricto:
        from .preparacion_documental import exigir_preparacion
        exigir_preparacion(documento, contenido_pdf, inicio, fin)
        from .recursos_periodo import es_esquema_recursos, fijar_recursos
        if tipo in ('planificacion', 'informe') and es_esquema_recursos(contenido_pdf):
            contenido_pdf = fijar_recursos(documento, inicio, fin, contenido_pdf, actualizar=True)
            redaccion.contenido = contenido_pdf
        if tipo == 'compras' and contenido_pdf.get('pac_version') == 2:
            from .diagnostico_compras import fijar_diagnostico
            contenido_pdf = fijar_diagnostico(documento, contenido_pdf, actualizar=True)
            from .priorizacion_necesidades import fijar_gestion_inversion
            contenido_pdf = fijar_gestion_inversion(documento, contenido_pdf, actualizar=True)
            redaccion.contenido = contenido_pdf
    compuesto = componer(documento, contenido_pdf, inicio, fin)
    compuesto['borrador'] = not estricto
    if getattr(documento, '_token_emision', None):
        from .contenido_emitido import conservar_compuesto
        documento._contenido_emitido = conservar_compuesto(compuesto)
    return render_documento_pdf(compuesto)


def pdf_acciones_de_mejora(documento, inicio, fin, *, borrador=False):
    """Seguimiento de acciones de mejora consolidado desde los informes semestrales del año."""
    from apps.documentos.presentation.expediente_pdf import render_documento_pdf
    from apps.documentos.models.mejora import AccionMejora

    informes = DocumentoElaborado.objects.filter(
        documento__unidad=documento.unidad, documento__anio=documento.anio,
        documento__exigido__fuente_reporte='informe',
    ).filter(Q(documento__corte=documento.corte) | Q(documento__corte='')).select_related('documento')
    filas = []
    for informe in informes:
        for accion in informe.contenido.get('acciones') or []:
            filas.append([informe.documento.etiqueta_corte, accion.get('hallazgo', '—'), accion.get('accion', '—'),
                          accion.get('responsable', '—'), accion.get('plazo', '—'),
                          _etiqueta(ESTADOS_ACCION, accion.get('estado', '')) or '—'])
    bloques = ([{'tipo': 'tabla', 'titulo': 'Acciones registradas en los informes semestrales',
                 'cabecera': ['Período', 'Hallazgo', 'Acción', 'Responsable', 'Plazo', 'Estado'], 'filas': filas}]
               if filas else [{'tipo': 'vacio', 'texto': 'Los informes del período no registran acciones de mejora.'}])
    secciones = [{'numero': 1, 'codigo': 'mejora', 'titulo': 'Acciones de mejora y su estado',
                  'bloques': bloques}]
    acciones = AccionMejora.objects.filter(
        informe__unidad=documento.unidad, informe__anio=documento.anio,
    ).filter(Q(informe__corte=documento.corte) | Q(informe__corte='')).select_related(
        'responsable', 'informe').prefetch_related('seguimientos__creado_por')
    filas_formales = []
    avances = []
    for accion in acciones:
        filas_formales.append([
            str(accion.pk), accion.descripcion, str(accion.responsable), accion.vence_el.isoformat(),
            'Cerrada' if accion.cerrada_en else 'Pendiente', accion.informe.get_decision_display()])
        avances.extend([str(accion.pk), timezone.localtime(avance.creado_en).strftime('%d/%m/%Y %H:%M'),
                        str(avance.creado_por), avance.detalle, 'Sí' if avance.cierre else 'No']
                       for avance in accion.seguimientos.all())
    if filas_formales:
        bloques.append({'tipo': 'tabla', 'titulo': 'Acciones derivadas de la resolución de la dependencia',
                        'cabecera': ['N.º', 'Acción', 'Responsable', 'Plazo', 'Estado', 'Resolución'],
                        'filas': filas_formales})
    if avances:
        bloques.append({'tipo': 'tabla', 'titulo': 'Seguimiento registrado',
                        'cabecera': ['Acción', 'Fecha', 'Autor', 'Avance y evidencia', 'Cierre verificado'],
                        'filas': avances})
    incumplidos = incumplimientos_del_periodo(documento)
    if incumplidos:
        # Un incumplimiento del expediente es un hallazgo: entra aquí sin que
        # nadie lo transcriba, porque es lo que la unidad tiene que corregir.
        secciones.append({
            'numero': 2, 'codigo': 'incumplimiento',
            'titulo': 'Incumplimientos del expediente en el período',
            'bloques': [
                {'tipo': 'parrafo', 'texto':
                    'El seguimiento del expediente registra estas entregas fuera de plazo u observadas. '
                    'Cada una exige una acción de mejora con responsable y plazo en el próximo informe.'},
                {'tipo': 'tabla', 'titulo': 'Entregas incumplidas',
                 'cabecera': ['Documento', 'Período', 'Estado', 'Venció', 'Atraso', 'Motivo'],
                 'filas': incumplidos},
            ],
        })
    return render_documento_pdf({
        'tipo': 'mejora', 'titulo': 'Seguimiento de acciones de mejora',
        'codigo_formato': referencia_interna(documento) if es_unidad_auditable(documento.unidad) else 'AP-P-LAP-GO · Mejora',
        'codigo_etiqueta': 'Referencia interna' if es_unidad_auditable(documento.unidad) else 'Código',
        'documento': documento,
        'borrador': borrador,
        'unidad': documento.unidad, 'periodo': documento.etiqueta_corte, 'tramo': (inicio, fin),
        'version': documento.version + 1,
        'secciones': secciones,
        'firmas': [],
    })


def incumplimientos_del_periodo(documento):
    """Las entregas vencidas u observadas de la unidad, como filas de hallazgo.

    Sale del mismo cálculo que ve la Dirección en su tablero: lo que allí
    aparece en rojo es lo que aquí la unidad tiene que explicar y corregir.
    """
    from apps.documentos.presentation.cumplimiento import incumplimientos
    from apps.documentos.presentation.expediente import leer_expediente

    documentos = [
        otro for otro in leer_expediente(documento.unidad, documento.anio)
        if not documento.corte or otro.corte in ('', documento.corte)
    ]
    return [
        [falta['documento'].nombre_documental, falta['documento'].etiqueta_corte, falta['etiqueta'],
         f'{falta["documento"].vence_el:%d/%m/%Y}' if falta['documento'].vence_el else '—',
         f'{falta["dias"]} días' if falta['dias'] else '—', falta['motivo']]
        for falta in incumplimientos(documentos)
        if falta['documento'].exigido.carpeta != 'mejora'
    ]


# -- vistas -----------------------------------------------------------------------

def _documento_redactable(request, slug, documento_id):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, 'reportes'):
        raise PermissionDenied('No tienes autorización para redactar documentos de esta unidad.')
    documento = get_object_or_404(
        DocumentoExpediente.objects.select_related('exigido', 'unidad'), pk=documento_id, unidad=unidad)
    if not documento.exigido.redactable:
        raise Http404('Este documento no se redacta con el editor.')
    return unidad, documento


def _campos_para_editor(tipo, contenido, unidad, documento, inicio, fin, registros, diagnostico_compra=None):
    """Apartados con sus campos y valores, listos para la plantilla."""
    secciones = []
    for numero, seccion in enumerate(secciones_de(tipo, unidad, contenido), start=1):
        campos = []
        for campo in seccion.campos:
            valor = contenido.get(campo.clave)
            dato = {'campo': campo, 'valor': valor}
            if tipo == 'protocolo':
                from .protocolo_contexto import opciones_editor
                dato['protocolo'] = opciones_editor(documento, campo, valor)
            if campo.tipo == 'rico':
                dato['html'] = html_del_campo(campo, valor)
                dato['politica'] = politica_de(campo)
            elif campo.tipo == 'marcas':
                dato['valor'] = list(valor or [])
            elif campo.tipo == 'tabla':
                dato['valor'] = list(valor or [])
                if tipo == 'compras' and campo.clave == 'compras' and contenido.get('pac_version') in (1, 2):
                    from .pac_universitario import datos_editor_pac
                    dato.update(datos_editor_pac(contenido, unidad=unidad, diagnostico=diagnostico_compra))
                    dato['pac'] = True
            elif campo.tipo == 'presupuesto_uso':
                from .presupuesto_uso import datos_presupuesto
                dato.update(datos_presupuesto(valor, inicio, fin))
            elif campo.tipo == 'actividades':
                contenido_editor = dict(contenido)
                if documento.estado not in ('validado', 'cargado'):
                    plan_editor = dict(contenido.get('actividades') or {}, minimos_catalogo=3)
                    contenido_editor['actividades'] = _aplicar_cronograma(plan_editor,
                        cronograma_automatico(unidad, inicio, fin, documento=documento))
                    from .metas_estandar import aplicar_metas, calcular_metas
                    from .politica_metas_unidades import capacidad_de
                    capacidad_actual = capacidad_de(unidad, inicio, fin)
                    plan_editor = contenido_editor['actividades']
                    plan_editor['capacidad'] = capacidad_actual
                    contenido_editor['actividades'] = aplicar_metas(plan_editor, calcular_metas(unidad, inicio, fin,
                        actividades_para(unidad, funciones=contenido.get('sectores'), capacidad=capacidad_actual),
                        capacidad_actual, plan_editor['cronograma_auto']))
                dato['cronograma_auto'] = (contenido_editor.get('actividades') or {}).get('cronograma_auto')
                dato['metas_estandar'] = (contenido_editor.get('actividades') or {}).get('metas_estandar')
                dato['valor'] = contenido_editor.get('actividades')
                dato['capacidad'] = (contenido_editor.get('actividades') or {}).get('capacidad')
                dato['filas'] = [f for f in filas_del_plan(unidad, contenido_editor, inicio, fin)
                                 if f['codigo'] != 'USO-EFECTIVO']
                dato['filas'].sort(key=lambda f: ORDEN_PLAN.index(f['codigo'])
                    if f['codigo'] in ORDEN_PLAN else len(ORDEN_PLAN))
                plan_editor = contenido_editor.get('actividades') or {}
                from apps.documentos.presentation.politica_metas_unidades import capacidad_de, ficha_indicador
                capacidad = dato['capacidad'] or capacidad_de(unidad, inicio, fin)
                dato['capacidad'] = capacidad
                actividades = {a.codigo: a for a in actividades_para(unidad,
                    version=plan_editor.get('minimos_catalogo', 3 if not plan_editor else 0),
                    funciones=contenido_editor.get('sectores'), capacidad=capacidad)}
                for fila in dato['filas']:
                    if fila['codigo'] in actividades:
                        fila['ficha_indicador'] = ficha_indicador(actividades[fila['codigo']], capacidad)
                        fila['control_meta'] = control_meta(actividades[fila['codigo']], fila['meta'], fila['aplica'],
                                                           proponer=documento.estado not in ('validado', 'cargado'))
                        if fila['control_meta']['numerica']:
                            fila['control_meta']['fija'] = True
                        if fila.get('meta_origen'):
                            ficha = fila['ficha_indicador']
                            ficha['pares'] = [('Meta calculada del semestre', fila['meta']),
                                ('Origen del cálculo', fila['meta_origen']), ('Cálculo del cumplimiento', ficha['formula']),
                                ('Respaldo necesario', ficha['evidencia']), ('Administración de la regla',
                                'Dirección administra las reglas. La unidad no modifica los números del catálogo. '
                                'La referencia y sus fuentes se conservan con el plan al guardarlo y con el cierre al enviarlo.')]
                        if documento.estado not in ('validado', 'cargado') and fila['control_meta'].get('ajustada'):
                            fila['meta'] = meta_con_minimo(actividades[fila['codigo']], fila['control_meta']['valor'])
                dato['meses'] = meses_del_tramo(inicio, fin)
            elif campo.tipo == 'cumplimiento':
                dato.update(filas_de_cumplimiento(documento, contenido, inicio, fin, registros))
            campos.append(dato)
        secciones.append({'numero': numero, 'seccion': seccion, 'campos': campos})
    campos = [dato for seccion in secciones for dato in seccion['campos']]
    politica = next((dato.get('metas_estandar') for dato in campos if dato['campo'].tipo == 'actividades'), None)
    if politica and politica.get('version') == 2 and politica['carga_docente'].get('aplica'):
        for dato in campos:
            if dato['campo'].tipo == 'presupuesto_uso':
                dato['carga_docente'] = politica['carga_docente']
                for mes in dato['meses']:
                    mes['horas_docentes'] = politica['carga_docente']['horas_por_mes'].get(str(mes['numero']), '0')
    return secciones


def _sugerencias_para_editor(documento, usuario, fin):
    from apps.finanzas.presentation.presupuesto import sugerencias_de_compra
    horizonte = date(documento.anio + 1, 12, 31) if documento.exigido.fuente_reporte == 'compras' else fin
    sugerencias = sugerencias_de_compra(documento.unidad, hasta=horizonte)
    puede_ver_ficha = (puede_operar_modulo_unidad(usuario, documento.unidad, 'recursos')
                      or puede_operar_modulo_unidad(usuario, documento.unidad, 'mantenimiento'))
    if not puede_ver_ficha:
        for sugerencia in sugerencias:
            sugerencia['url_equipo'] = ''
    return sugerencias


def _unir_sugerencias_compra(sugerencias, contraste):
    """Añade referencias por revisar sin desplazar las propuestas originales."""
    resultado = list(sugerencias or [])
    claves = {p.get('clave') for p in resultado if isinstance(p, dict) and p.get('clave')}
    for area in (contraste or {}).get('areas') or []:
        if not isinstance(area, dict):
            continue
        for propuesta in area.get('sugerencias') or []:
            if not isinstance(propuesta, dict):
                continue
            clave = propuesta.get('clave')
            if clave and clave not in claves:
                resultado.append(propuesta)
                claves.add(clave)
    return resultado


@login_required
@require_http_methods(['GET', 'POST'])
def redactar_documento_view(request, slug, documento_id):
    from apps.documentos.presentation.expediente import tramo_del_documento

    unidad, documento = _documento_redactable(request, slug, documento_id)
    tipo = documento.exigido.fuente_reporte
    redaccion = obtener_redaccion(documento)
    inicio, fin = tramo_del_documento(documento)
    destino_expediente = (reverse('gestion_expediente_unidad', args=[slug])
                          + f'?anio={documento.anio}&corte={documento.corte}')
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        version_base = request.POST.get('version_base', '')
        if request.POST.get('accion') in ('generar_guardado', 'generar_enviar_guardado'):
            # La vista previa envía la versión que mostró, no una segunda copia
            # de los campos. Generar nunca debe vaciar ni volver a guardar la
            # redacción existente, y una pestaña obsoleta no emite otro PDF.
            with transaction.atomic():
                Unidad.objects.select_for_update().get(pk=unidad.pk)
                documento.refresh_from_db()
                redaccion = obtener_redaccion(documento)
                if (not version_base.isdigit() or int(version_base) != redaccion.version
                        or documento.estado in ('validado', 'cargado')):
                    error = ('El documento cambió o ya fue enviado. '
                             'Abre la versión actual y vuelve a aplicar tus cambios.')
                    if es_ajax:
                        return JsonResponse({'success': False, 'conflicto': True, 'error': error}, status=409)
                    messages.error(request, error)
                    return redirect(request.path)
                from apps.documentos.presentation.expediente import generar_documento
                try:
                    if request.POST.get('accion') == 'generar_enviar_guardado':
                        from .aprobacion_en_linea import generar_y_enviar_qr
                        generar_y_enviar_qr(documento, request.user, request=request)
                    else:
                        generar_documento(documento, request.user, request=request)
                except ValidationError as error:
                    if es_ajax:
                        return JsonResponse({'success': False, 'error': ' '.join(error.messages)}, status=400)
                    messages.error(request, ' '.join(error.messages))
                    return redirect(request.path)
            if es_ajax:
                documento.refresh_from_db()
                return JsonResponse(dict(success=True, url=reverse('recurso_unidad', args=[documento.recurso_id]),
                    descarga=reverse('recurso_unidad', args=[documento.recurso_id]) + '?download=1',
                    titulo=f'Documento · {documento.nombre_documental}', recurso=documento.recurso_id,
                    enviado=documento.estado == 'validado',
                    version=redaccion.version))
            messages.success(request, 'Documento enviado a Dirección.' if documento.estado == 'validado' else
                'Documento preparado. Puedes enviarlo a Dirección desde el expediente.' if documento.verificacion_qr else
                'Documento generado. Descárgalo, fírmalo y cárgalo en el expediente.')
            return redirect(destino_expediente)
        try:
            contenido = leer_formulario(tipo, request.POST, unidad, inicio=inicio, fin=fin,
                documento=documento, contenido_anterior=redaccion.contenido)
        except ValidationError as error:
            mensaje = ' '.join(error.messages)
            if es_ajax:
                return JsonResponse({'success': False, 'error': mensaje}, status=400)
            messages.error(request, mensaje)
            return redirect(request.path)
        with transaction.atomic():
            Unidad.objects.select_for_update().get(pk=unidad.pk)
            documento.refresh_from_db()
            redaccion = obtener_redaccion(documento)
            if (not version_base.isdigit() or int(version_base) != redaccion.version
                    or documento.estado in ('validado', 'cargado')):
                error = ('El documento cambió o ya fue enviado. '
                         'Abre la versión actual y vuelve a aplicar tus cambios.')
                if es_ajax:
                    return JsonResponse({'success': False, 'conflicto': True, 'error': error}, status=409)
                messages.error(request, error)
                return redirect(request.path)
            # obtener_redaccion adapta propuestas para el editor sin guardarlas.
            # La auditoría debe conservar el JSON realmente persistido antes del POST.
            anteriores = DocumentoElaborado.objects.filter(pk=redaccion.pk).values(
                'version', 'contenido').first() or {'version': 0, 'contenido': {}}
            if tipo == 'planificacion' and not request.POST.get('uso_presupuesto_presente'):
                contenido['presupuesto_uso'] = (redaccion.contenido or {}).get('presupuesto_uso', {})
            redaccion.contenido = contenido
            redaccion.version += 1
            redaccion.actualizado_por = request.user
            redaccion.save()
            registrar_auditoria(
                request, unidad=unidad, accion='actualizar', objeto=redaccion,
                descripcion=f'{documento.nombre_documental} {documento.etiqueta_corte}: borrador guardado',
                anteriores=anteriores, nuevos={'version': redaccion.version, 'contenido': contenido})
        from .preparacion_documental import preparacion_del_editor
        progreso = preparacion_del_editor(documento, contenido, inicio, fin)
        if es_ajax:
            identidades_pac = {}
            if tipo == 'compras':
                from .pac_universitario import identidades_formulario_pac
                identidades_pac['pac_identidades'] = identidades_formulario_pac(request.POST, contenido)
            return JsonResponse({
                'success': True, 'version': redaccion.version,
                'guardado_en': timezone.localtime(redaccion.actualizado_en).strftime('%H:%M'),
                'porcentaje': progreso['porcentaje'],
                'requeridos': progreso['requeridos'], 'llenos': progreso['llenos'],
                'faltantes': faltantes_del_editor(progreso),
                'secciones': progreso['secciones'],
                **identidades_pac,
            })
        accion = request.POST.get('accion', 'guardar')
        if accion == 'generar':
            from apps.documentos.presentation.expediente import generar_documento
            try:
                generar_documento(documento, request.user, request=request)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
                return redirect(request.path)
            messages.success(request, 'Documento preparado. Puedes enviarlo a Dirección desde el expediente.'
                if documento.verificacion_qr else 'Documento generado. Descárgalo, fírmalo y cárgalo en el expediente.')
            return redirect(destino_expediente)
        messages.success(request, 'Borrador guardado.')
        if accion == 'vista_previa':
            return redirect(reverse('vista_previa_documento_expediente', args=[slug, documento.pk]))
        return redirect(request.path)

    contenido_guardado = deepcopy(redaccion.contenido or {})
    if documento.estado not in ('validado', 'cargado'):
        if tipo == 'planificacion':
            from .recursos_periodo import preparar_recursos
            redaccion.contenido = preparar_recursos(redaccion.contenido)
        elif tipo == 'compras':
            from .pac_universitario import preparar_pac
            redaccion.contenido = preparar_pac(redaccion.contenido, unidad=unidad)
    contenido = redaccion.contenido or {}
    automaticos = datos_automaticos(documento, inicio, fin, contenido)
    from .preparacion_documental import preparacion_del_editor
    progreso = preparacion_del_editor(documento, contenido, inicio, fin)
    secciones = _campos_para_editor(tipo, contenido, unidad, documento, inicio, fin, automaticos.get('_registros'),
                                   diagnostico_compra=automaticos.get('_diagnostico_compras'))
    contraste_compras = next((dato.get('contraste_pac') for seccion in secciones for dato in seccion['campos']
        if dato['campo'].clave == 'compras'), None) if tipo == 'compras' else None
    sugerencias_compra = []
    if tipo == 'compras':
        sugerencias_compra = (_unir_sugerencias_compra(
            (automaticos.get('_diagnostico_compras') or {}).get('sugerencias', []), contraste_compras)
            if contenido.get('pac_version') == 2 else _sugerencias_para_editor(documento, request.user, fin))
    contenido_revision = contenido
    if tipo == 'planificacion' and documento.estado not in ('validado', 'cargado'):
        plan_editor = next((dato['valor'] for seccion in secciones for dato in seccion['campos']
                            if dato['campo'].tipo == 'actividades'), contenido.get('actividades'))
        contenido_revision = dict(contenido, actividades=plan_editor)
    return render(request, 'portal/pages/unidades/gestion/expediente_editor.html', {
        'page_key': 'editor-expediente',
        'page_title': f'{documento.nombre_documental if es_unidad_auditable(unidad) else NOMBRES_TIPO[tipo]} · {unidad.nombre}',
        'unidad': unidad,
        'documento': documento,
        'redaccion': redaccion,
        'tipo': tipo,
        'nombre_tipo': (NOMBRES_TIPO[tipo] if tipo == 'compras' and contenido.get('pac_version') == 2 else
                        documento.nombre_documental if es_unidad_auditable(unidad) else NOMBRES_TIPO[tipo]),
        'pendientes_actividades': pendientes_actividades(unidad, contenido_revision, inicio, fin) if tipo == 'planificacion' else [],
        'plan_recalculado': contenido_revision != contenido_guardado,
        'aprobacion_en_linea': documento.aprobacion_en_linea_disponible,
        'envio_qr_disponible': documento.aprobacion_en_linea_disponible and (
            documento.exigido.codigo != 'INFORME-SEMESTRAL' or timezone.localdate() > fin),
        'codigo_formato': referencia_interna(documento) if es_unidad_auditable(unidad) else CODIGOS_FORMATO[tipo],
        'codigo_etiqueta': 'Referencia interna' if es_unidad_auditable(unidad) else 'Código',
        'inicio': inicio, 'fin': fin,
        'secciones': secciones,
        'automaticos': automaticos,
        'progreso': progreso,
        'faltantes': faltantes_del_editor(progreso),
        'url_expediente': destino_expediente,
        'url_vista_previa': reverse('vista_previa_documento_expediente', args=[slug, documento.pk]),
        'url_pdf_borrador': reverse('pdf_borrador_documento_expediente', args=[slug, documento.pk]),
        'url_pdf_firma': (reverse('recurso_unidad', args=[documento.recurso_id])
            if documento.estado == 'generado' and documento.recurso_id
            and redaccion.generado_version == redaccion.version and contenido_revision == contenido_guardado else ''),
        'url_pdf_preparado_anterior': (reverse('recurso_unidad', args=[documento.recurso_id])
            if documento.estado == 'generado' and documento.recurso_id
            and (redaccion.generado_version != redaccion.version or contenido_revision != contenido_guardado) else ''),
        'sugerencias': sugerencias_para(documento, POLITICAS_RICAS),
        'sugerencias_compra': sugerencias_compra,
        'contraste_compras': contraste_compras,
        'diagnostico_compras': automaticos.get('_diagnostico_compras'),
        'respaldo_compras': automaticos.get('_respaldo_compras'),
        'tabla_compras': 'compras' if tipo == 'compras' else '',
        'url_exportar_pac': reverse('exportar_pac_unidad', args=[unidad.slug, documento.pk]) if tipo == 'compras' else '',
        'anio_planificado': documento.anio + 1 if tipo == 'compras' else None,
        'priorizacion_inversion': automaticos.get('_priorizacion_inversion'),
        'protocolo_fuentes': contenido.get('_protocolo_fuentes', '') if tipo == 'protocolo' else '',
    })


@login_required
@require_http_methods(['GET'])
def pdf_borrador_documento_view(request, slug, documento_id):
    """El PDF tal como saldría ahora, para el visor en modal; no se archiva."""
    from django.http import HttpResponse

    from apps.documentos.presentation.expediente import tramo_del_documento

    unidad = get_object_or_404(Unidad, slug=slug)
    mejora = DocumentoExpediente.objects.filter(
        pk=documento_id, unidad=unidad, exigido__fuente_reporte='mejora').select_related('exigido', 'unidad').first()
    if mejora is not None:
        # El anexo de acciones de mejora se consolida desde los informes: la vista previa es el mismo PDF que se
        # archiva, no la consulta del Centro de reportes.
        if not puede_operar_modulo_unidad(request.user, unidad, 'reportes'):
            raise PermissionDenied('No tienes autorización para consultar documentos de esta unidad.')
        documento = mejora
        inicio, fin = tramo_del_documento(documento)
        contenido = pdf_acciones_de_mejora(documento, inicio, fin, borrador=True)
    else:
        unidad, documento = _documento_redactable(request, slug, documento_id)
        redaccion = obtener_redaccion(documento)
        inicio, fin = tramo_del_documento(documento)
        contenido = pdf_del_documento(documento, redaccion, inicio, fin, estricto=False)
    respuesta = HttpResponse(contenido, content_type='application/pdf')
    nombre = f'{documento.exigido.codigo}-{documento.anio}{documento.corte}-borrador.pdf'
    respuesta['Content-Disposition'] = f'inline; filename="{nombre}"'
    return respuesta


@login_required
@require_http_methods(['GET'])
def vista_previa_documento_view(request, slug, documento_id):
    from apps.documentos.presentation.expediente import tramo_del_documento

    unidad, documento = _documento_redactable(request, slug, documento_id)
    redaccion = obtener_redaccion(documento)
    inicio, fin = tramo_del_documento(documento)
    compuesto = componer(documento, redaccion.contenido or {}, inicio, fin)
    from .preparacion_documental import preparacion_del_editor
    progreso = preparacion_del_editor(documento, redaccion.contenido or {}, inicio, fin)
    return render(request, 'portal/pages/unidades/gestion/expediente_vista.html', {
        'unidad': unidad,
        'documento': documento,
        'redaccion': redaccion,
        'compuesto': compuesto,
        'progreso': progreso,
        'faltantes': faltantes_del_editor(progreso),
        'url_editor': reverse('redactar_documento_expediente', args=[slug, documento.pk]),
        'url_pdf_borrador': reverse('pdf_borrador_documento_expediente', args=[slug, documento.pk]),
        'url_expediente': (reverse('gestion_expediente_unidad', args=[slug])
                           + f'?anio={documento.anio}&corte={documento.corte}'),
    })
