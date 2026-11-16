"""Adaptador de trazabilidad documental; la valoración cualitativa conserva revisión humana."""
from apps.documentos.models.expediente import DocumentoExigido
from apps.gestion_unidades.presentation.reportes_perfiles import dataset_perfil
from apps.documentos.presentation.medicion_perfiles import base_perfil

FUENTES_PERFIL = {'OBS-BOLETINES': 'boletines', 'OBS-DATOS': 'datos-observatorio',
    'OBS-EVENTOS': 'eventos', 'CE-ENSAYOS': 'ensayos', 'CE-PRODUCCION': 'produccion-agropecuaria',
    'PP-CALIDAD': 'control-calidad', 'PP-PRODUCCION': 'produccion'}
BASES_DOCUMENTO = {'OBS-BOLETINES': 'observatorios', 'OBS-DATOS': 'observatorios',
    'OBS-EVENTOS': 'observatorios', 'CE-ENSAYOS': 'centro_experimental',
    'CE-PRODUCCION': 'centro_experimental', 'PP-CALIDAD': 'plantas_piloto', 'PP-PRODUCCION': 'plantas_piloto'}
# Anexos que son registro del período y no tienen evidencia de revisión técnica: en ellos se
# comprueba que cada registro de origen tenga los datos para seguirlo.
SIN_REVISION_TECNICA = frozenset(('CE-PRODUCCION',))
DETALLE_MAXIMO = 5  # Ciclos que se nombran en el hallazgo; los demás se cuentan.


def _trazabilidad_incompleta(capturas):
    """Mensaje con los ciclos productivos a los que les faltan datos, o '' si todos pueden seguirse."""
    incompletos = [(c.get('nombre') or f"ciclo {c.get('id')}", c['pendientes']) for c in capturas if c.get('pendientes')]
    if not incompletos:
        return ''
    detalle = '; '.join(f"{nombre}: {', '.join(pendientes)}" for nombre, pendientes in incompletos[:DETALLE_MAXIMO])
    if len(incompletos) > DETALLE_MAXIMO:
        detalle += f'; y {len(incompletos) - DETALLE_MAXIMO} más'
    cuantos = ('1 ciclo productivo tiene' if len(incompletos) == 1
               else f'{len(incompletos)} ciclos productivos tienen')
    return f'{cuantos} datos por completar para seguir su producción. Falta, por ciclo: {detalle}.'


def analizar_perfil(contexto, codigo):
    if codigo not in FUENTES_PERFIL:
        return None
    fuente = FUENTES_PERFIL[codigo]
    hallazgos = []
    def hallar(regla, mensaje, severidad='bloqueo'):
        contexto._hallazgo(hallazgos, regla, mensaje, severidad=severidad)
    if base_perfil(contexto.unidad) != BASES_DOCUMENTO[codigo]:
        hallar('TIPOLOGIA_DE_FUENTE_INCORRECTA', 'La fuente de este documento pertenece a otro tipo de unidad.')
        return dict(codigo=codigo, automatico=False, hallazgos=hallazgos,
                    fuentes=dict(perfil=codigo, tipologia=base_perfil(contexto.unidad)))
    exigido = DocumentoExigido.objects.filter(codigo=codigo).select_related('anexo_de').first()
    if (exigido is None or not exigido.activo or not exigido.automatico or
            exigido.fuente_reporte != fuente or not exigido.anexo_de_id or
            exigido.anexo_de.codigo != 'INFORME-SEMESTRAL'):
        hallar('CONTRATO_PERFIL_MODIFICADO', 'El documento no conserva el contrato de fuente y anexo previsto para el perfil.')
    if exigido and not exigido.aplica_a(contexto.unidad.dependencia, base=base_perfil(contexto.unidad)):
        hallar('DOCUMENTO_NO_APLICA_AL_PERFIL', 'El catálogo vigente no asigna este documento al tipo de esta unidad.')
    datos = contexto._una_vez(('perfil', codigo), lambda: dataset_perfil(
        fuente, contexto.unidad, contexto.inicio, contexto.fin))
    sin_revision = codigo in SIN_REVISION_TECNICA
    if sin_revision:
        # No hay revisión técnica que exigir: lo que falte para seguir un ciclo lo resuelve una persona.
        incompleta = _trazabilidad_incompleta(datos['fuentes_nativas'])
        if incompleta:
            hallar('TRAZABILIDAD_PRODUCCION_INCOMPLETA', incompleta, 'revision')
    else:
        pendientes = datos['cards'][2][1] if datos['cards'] else 0
        if pendientes:
            hallar('FUENTES_PERFIL_SIN_REVISION',
                f'{pendientes} registros de origen no tienen comprobación técnica vigente, completa y atribuida a esta unidad.')
    no_aplica = datos['mediciones'].get('cobertura_calidad', {}).get('no_aplica_verificado')
    if not datos['rows'] and not no_aplica:
        hallar('PERFIL_SIN_REGISTROS', 'No hay registros de origen para este período; documenta el alcance antes de darlo por conforme.', 'revision')
    if fuente == 'control-calidad':
        medida = datos['mediciones'].get('cobertura_calidad', {})
        if medida.get('pendiente') or medida.get('numerador') != medida.get('denominador'):
            hallar('COBERTURA_CALIDAD_PENDIENTE', medida.get('motivo') or
                'Falta comprobar los controles de todos los lotes u órdenes finalizados del período.')
    return dict(codigo=codigo, automatico=not hallazgos, hallazgos=hallazgos,
        fuentes=dict(perfil=codigo, nativos=datos['fuentes_nativas'],
                     mediciones=datos['mediciones'],
                     # Sin evidencias de revisión no hay tabla de respaldos: la última es de registros.
                     respaldos=[] if sin_revision else datos['tablas'][-1]['rows'],
                     contenido_reporte=dict(cabecera=datos['headers'], filas=datos['rows'],
                         tablas=datos['tablas'], truncado=datos.get('truncated', False))),
        alcance=('Comprobación automática de trazabilidad e integridad de los registros de origen. '
                 'No califica el manejo ni el rendimiento de los ciclos.' if sin_revision else
                 'Comprobación automática de trazabilidad, integridad y revisión técnica. '
                 'No califica por sí sola la pertinencia de la metodología ni las conclusiones.'))
