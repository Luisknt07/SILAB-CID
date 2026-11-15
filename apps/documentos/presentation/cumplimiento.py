"""Cumplimiento del expediente: qué entregó cada unidad y qué le falta.

La Dirección no puede auditar unidad por unidad abriendo veinte consolas. Aquí
está la lectura que necesita: por período, cuánto de lo exigido está validado,
qué espera su decisión, qué venció y qué todavía no abre su ventana, con un
semáforo por unidad y el detalle de lo incumplido para exigirlo.

Lo incumplido no se queda en una cifra: alimenta el reporte de incumplimiento,
que es el hallazgo con el que la unidad abre su acción de mejora.
"""

from datetime import date

from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.core.presentation.tipologias import tipologias_actuales

from apps.documentos.models.expediente import NOMBRES_ETAPA, es_calificable, minimo_vigente, politica_consistente

from apps.documentos.presentation.expediente import NOMBRES_SEMAFORO, leer_expediente, leer_expedientes, cortes_del_anio, del_periodo, resumen
from apps.documentos.presentation.progreso_general import (
    acreditacion_actual, completar_acreditacion_actual, progreso_general,
)
from apps.core.presentation.pdf_institucional import fuentes_documento, hoja_de_estilos

# Tipos de unidad que el expediente audita. Los centros de investigación y
# desarrollo llevan otro ciclo y tendrán su propio centro de reportes.
DEPENDENCIAS_AUDITADAS = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')

SEMAFOROS_UNIDAD = {
    'incumple': ('Incumple', 'Tiene entregas vencidas u observadas'),
    'en_riesgo': ('En riesgo', 'Sin vencidos, pero con entregas por vencer o esperando validación'),
    'al_dia': ('Al día', 'Todo lo exigible del período está validado o en plazo'),
}


def completar_controles_de_lectura(documentos):
    """Adjunta únicamente controles guardados, compartiendo una carga por listado."""
    from apps.documentos.presentation.automatizacion_documental import completar_controles
    documentos = list(documentos)
    from .aprobacion_en_linea import completar_constancias
    completar_constancias(documentos)
    pendientes = [d for d in documentos if d.unidad_id and not hasattr(d, 'automatizacion')]
    if pendientes:
        completar_controles(pendientes)
    from apps.documentos.presentation.progreso_documento import completar_avances
    completar_avances(documentos)
    return documentos


def resumen_controles_de_lectura(documentos):
    """Cuenta únicamente atributos precargados; no consulta la tabla del control."""
    from apps.documentos.presentation.automatizacion_documental import resumen_automatizacion
    return resumen_automatizacion(documentos)


def clasificacion_bandeja_automatizacion(documento, control=None):
    """Separa decisiones de Dirección y faltantes de la unidad sin analizar fuentes."""
    from apps.documentos.presentation.expediente_interfaz import evaluacion_humana_vigente

    if documento.estado == 'no_aplica':
        return ''
    control = getattr(documento, 'automatizacion', {}) if control is None else control
    control = control or {}
    estado = control.get('estado', 'sin_analizar')
    if not control.get('vigente') or estado in ('sin_analizar', 'desactualizado'):
        return 'sin_analizar'
    decision = (control.get('resumen') or {}).get('decision_automatica') or {}
    if decision.get('version') == 1 and decision.get('destino') in ('automatico', 'unidad', 'direccion'):
        from .decision_automatica import excepcion_resuelta_por_revision
        if excepcion_resuelta_por_revision(documento, control):
            return 'unidad' if decision.get('faltantes_unidad') else ''
        return {'automatico': 'automatico', 'unidad': 'unidad', 'direccion': 'excepciones'}[decision['destino']]
    if estado == 'automatico':
        return 'excepciones' if control.get('resumen', {}).get('requiere_seguimiento') else 'automatico'
    if documento.estado != 'validado':
        return 'unidad' if estado in ('revision', 'bloqueado', 'sin_archivo') else ''
    if getattr(getattr(documento, 'exigido', None), 'es_anexo', False):
        return ''
    if estado not in ('revision', 'bloqueado'):
        return ''
    # Una decisión vigente ya resolvió el criterio humano. Sólo una alerta
    # explícita de integridad mantiene su seguimiento tras esa evaluación.
    critico = any(h.get('severidad') in ('critico', 'crítico', 'bloqueo_critico')
        or h.get('regla') == 'anexo_modificado'
        or (h.get('regla') == 'procedencia_no_comprobada'
            and control.get('resumen', {}).get('procedencia', {}).get('archivo_integro') is False)
        for h in control.get('hallazgos', []))
    if not evaluacion_humana_vigente(documento) or (estado == 'bloqueado' and critico):
        return 'excepciones'
    return ''


def filtrar_bandeja_automatizacion(filas, bandeja):
    """Recorta la bandeja visible; las notas y el denominador de cada unidad se conservan."""
    if not bandeja:
        return filas
    resultado = []
    for fila in filas:
        casillas = []
        for casilla in fila['matriz']:
            lectura = casilla['documento'].resumen_interfaz
            if not lectura.get('control_documental', lectura.get('laboratorio')):
                continue
            control = lectura.get('automatizacion') or {}
            if clasificacion_bandeja_automatizacion(casilla['documento'], control) == bandeja:
                casillas.append(casilla)
        anexos = [anexo for anexo in fila.get('anexos_seguimiento', ())
            if clasificacion_bandeja_automatizacion(anexo['documento']) == bandeja]
        if casillas or anexos:
            resultado.append(dict(fila, matriz=casillas, categorias_matriz=categorias_de_matriz(casillas),
                anexos_seguimiento=anexos,
                anexos_seguimiento_otros=[a for a in anexos if not a.get('es_soporte_planificacion')]))
    return resultado


def categorias_de_matriz(casillas, anexos=()):
    """Ordena la lectura sin alterar exigencias, avance ni permisos de cada entrega."""
    from .organizacion_expediente import casilla_de_soporte_planificacion

    categorias = {}
    casillas = list(casillas)
    soportes = [casilla_de_soporte_planificacion(anexo) for anexo in anexos
                if getattr(anexo['documento'], 'soporte_planificacion', None)]
    filas = []
    for casilla in casillas:
        documento = casilla['documento']
        filas.append(casilla)
        propios = [soporte for soporte in soportes if soporte['documento_padre'] is documento]
        filas.extend(propios)
        soportes = [soporte for soporte in soportes if soporte not in propios]
    # Una bandeja de excepciones puede mostrar sólo el respaldo. Se conserva
    # su categoría y el enlace al plan sin volver a introducir la obligación.
    filas.extend(soportes)
    for original in filas:
        casilla = dict(original)
        es_soporte = casilla.get('es_soporte_planificacion', False)
        documento = casilla['documento_padre'] if es_soporte else casilla['documento']
        exigido = documento.exigido
        lectura = getattr(documento, 'resumen_interfaz', {}) or {}
        periodicidad = getattr(documento, 'periodicidad_documental', None) or getattr(exigido, 'periodicidad', '')
        casilla['categoria_flujo'] = ('planificacion' if getattr(exigido, 'codigo', '') == 'PLANIFICACION' else
                                     'base' if periodicidad in ('unica', 'anual') else 'cierre')
        if getattr(exigido, 'es_anexo', False):
            clave, nombre, ayuda, orden = ('anexos', 'Anexos y seguimiento',
                'Respaldan las entregas principales; no suman una obligación ni un porcentaje independiente.', 3)
        elif lectura.get('permanente') or periodicidad == 'unica':
            clave, nombre, ayuda, orden = ('permanentes', 'Documentos permanentes de la unidad',
                'Se conservan entre períodos. Actualizar únicamente cuando cambien.', 0)
        elif periodicidad == 'anual':
            clave, nombre, ayuda, orden = ('anuales', f'Documentos del año {getattr(documento, "anio", "")}'.strip(),
                'Una entrega por año, con seguimiento de necesidades y prioridades.', 1)
        else:
            corte = getattr(documento, 'corte', '')
            etiqueta = getattr(documento, 'etiqueta_corte', '')
            clave, nombre, ayuda, orden = (f'semestre-{corte}', etiqueta or 'Documentos del semestre',
                'Planificación y resultados del mismo semestre. Dirección atiende las excepciones.', 2)
        if clave not in categorias:
            categorias[clave] = dict(codigo=clave, nombre=nombre, ayuda=ayuda,
                orden=orden, casillas=[], recibidos=0, total_obligaciones=0, soportes=0)
        categoria = categorias[clave]
        categoria['casillas'].append(casilla)
        categoria['soportes'] += bool(es_soporte)
        if not es_soporte:
            categoria['total_obligaciones'] += 1
            categoria['recibidos'] += bool(casilla.get('enviado'))
    return sorted(categorias.values(), key=lambda categoria: (categoria['orden'], categoria['codigo']))


def anexos_de_seguimiento(documentos, hoy=None):
    """Respaldos consultables fuera de las obligaciones y sus denominadores."""
    from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
    from .organizacion_expediente import contextualizar_soportes_planificacion

    hoy = hoy or timezone.localdate()
    documentos = contextualizar_soportes_planificacion(documentos)
    anexos = []
    for documento in documentos:
        if not documento.exigido.es_anexo or documento.estado == 'no_aplica':
            continue
        documento.resumen_interfaz = resumen_de_entrega(documento)
        documento.semaforo_actual = documento.semaforo(hoy)
        documento.nombre_semaforo = NOMBRES_SEMAFORO[documento.semaforo_actual]
        soporte = getattr(documento, 'soporte_planificacion', None)
        anexos.append({'documento': documento, 'es_soporte_planificacion': bool(soporte),
                       'soporte_planificacion': soporte, 'aporta_puntos': False})
    return sorted(anexos, key=lambda anexo: (anexo['documento'].exigido.orden,
        anexo['documento'].corte, anexo['documento'].nombre_documental))


def documentos_de_bandeja(fila):
    """Las mismas filas de la pantalla, incluidas las alertas de anexos sin peso."""
    return [casilla['documento'] for casilla in fila['matriz']] + [
        anexo['documento'] for anexo in fila.get('anexos_seguimiento', ())]


def nombre_del_tipo(codigo, plural=True):
    """Cómo se llama esa tipología en el catálogo institucional."""
    from apps.core.presentation.tipologias import tipologia

    actual = tipologia(codigo or '')
    return actual.etiqueta('es', plural=plural) if actual else (codigo or '—')


def tipos_auditados():
    """[(código, nombre)] de los tipos que el expediente audita, para los filtros."""
    return [(t.codigo, t.etiqueta('es', plural=True)) for t in tipologias_actuales()
            if t.base in DEPENDENCIAS_AUDITADAS]


def unidades_auditadas(usuario=None, dependencias=None):
    """Las unidades activas que el expediente audita, recortadas por quien mira."""
    solicitadas = set(dependencias or DEPENDENCIAS_AUDITADAS)
    codigos = {t.codigo for t in tipologias_actuales()
               if t.base in solicitadas or t.codigo in solicitadas}
    unidades = Unidad.objects.filter(dependencia__in=codigos, activo=True)
    if usuario is not None:
        from apps.gestion_unidades.presentation.permisos import unidades_del_expediente
        unidades = unidades.filter(pk__in=unidades_del_expediente(usuario))
    return unidades.order_by('dependencia', 'nombre')


def _meta_de(documento):
    """Qué se le exige a este documento, en una línea: cuándo y con qué condición."""
    exigido = documento.exigido
    if exigido.plazo_regla == 'inicio':
        cuando = f'primeros {exigido.plazo_dias} días del período'
    elif exigido.plazo_regla == 'fin':
        cuando = 'antes del cierre del período'
    elif exigido.plazo_regla == 'cierre':
        cuando = f'{exigido.plazo_dias} días después del cierre del semestre de gestión'
    elif exigido.plazo_regla == 'meses' and exigido.abre_mes and exigido.vence_mes:
        meses = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
                 'septiembre', 'octubre', 'noviembre', 'diciembre')
        cuando = f'entre {meses[exigido.abre_mes - 1]} y {meses[exigido.vence_mes - 1]}'
    else:
        cuando = 'una sola vez; se hereda cada año'
    firma = 'firmado' if exigido.requiere_firma else 'sin firma'
    return f'{cuando} · {firma}'


def _quien(usuario):
    return (usuario.get_full_name() or usuario.get_username()) if usuario else '—'


def _fecha(momento, formato='%d/%m/%Y %H:%M'):
    if momento is None:
        return ''
    return (timezone.localtime(momento) if timezone.is_aware(momento) else momento).strftime(formato)


def _rastro(documento):
    """Quién hizo qué con este documento: para que la Dirección compruebe, no crea.

    Un control de calidad transparente tiene que poder responder quién subió
    qué, quién lo dio por bueno y si el archivo es el mismo: por eso el rastro
    termina en la huella SHA-256 del PDF archivado.
    """
    from apps.documentos.presentation.expediente_interfaz import evaluacion_humana_vigente
    from .conformidad_lectura import lectura_conformidad

    conformidad = lectura_conformidad(documento)

    control = getattr(documento, 'automatizacion', {}) or {}
    control_actual = bool(control.get('vigente'))
    automatico = bool(control_actual and control.get('aplicado') and control.get('estado') == 'automatico')
    resumen_control = control.get('resumen') or {}
    pasos = []
    if documento.cargado_en:
        pasos.append(f'Cargó {_quien(documento.cargado_por)} · {_fecha(documento.cargado_en)}')
    elif documento.generado_en:
        pasos.append(f'Lo generó el sistema · {_fecha(documento.generado_en)}')
    if documento.tardanza_pedida_en:
        pasos.append(f'Pidió entregar fuera de plazo · {_fecha(documento.tardanza_pedida_en, "%d/%m/%Y")}')
    if documento.tardanza_habilitada_en:
        pasos.append(f'Habilitó {_quien(documento.tardanza_habilitada_por)} · '
                     f'{_fecha(documento.tardanza_habilitada_en, "%d/%m/%Y")}')
    if documento.validado_en and documento.estado == 'validado':
        if documento.validado_por_id:
            autor = f'Validó {_quien(documento.validado_por)}'
        elif automatico:
            autor = 'Validación automática: Sistema'
        else:
            autor = 'Validación registrada sin autor'
        pasos.append(f'{autor} · {_fecha(documento.validado_en)}')
    if documento.recibido_en:
        if documento.recibido_por_id:
            autor = f'Recibió la Dirección: {_quien(documento.recibido_por)}'
        elif control_actual and resumen_control.get('recepcion_automatica'):
            autor = 'Recepción técnica: Sistema'
        else:
            autor = 'Recepción registrada sin autor'
        pasos.append(f'{autor} · {_fecha(documento.recibido_en)}')
    if documento.evaluado_en:
        autor = (_quien(documento.evaluado_por) if documento.evaluado_por_id else
                 'el sistema por no entrega' if documento.incumplimiento_procesado_hasta else 'autor no registrado')
        accion = ('Revisión histórica' if conformidad and conformidad['historica'] else
                  'Comprobó conformidad' if conformidad else 'Calificó')
        pasos.append(f'{accion} {autor} · {_fecha(documento.evaluado_en)}')
    if automatico and control.get('nota') is not None and not evaluacion_humana_vigente(documento):
        fuente = ('Dirección · aprobación previa' if resumen_control.get('aprobacion_reutilizada') else 'Sistema')
        pasos.append(f'Conformidad: {conformidad["etiqueta"]} · {fuente}' if conformidad else
                     f'Resultado: {fuente} · {control["nota"]} %')
    if documento.ultimatum_hasta:
        pasos.append(f'Ultimátum colectivo hasta {_fecha(documento.ultimatum_hasta)}')
    if documento.recurso_id and documento.recurso.hash_sha256:
        pasos.append(f'SHA-256 {documento.recurso.hash_sha256[:16]}')
    return pasos


def _matriz(documentos, hoy):
    """Una fila por documento exigido: qué se pide, su evidencia y en qué paso va.

    Es la lectura con la que la Dirección decide: entregado, recibido, evaluado
    y si cumple, con el rastro y la observación al lado. Y con la acción que
    toca: recibir lo que la unidad archivó sin validar, habilitar una entrega
    vencida o calificar. Los anexos no salen: viajan dentro del documento
    firmado que los presenta.
    """
    from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega

    filas = []
    for documento in completar_acreditacion_actual(completar_controles_de_lectura(documentos)):
        if documento.exigido.es_anexo or not documento.exigible:
            continue
        enviado = documento.estado == 'validado'
        archivado = bool(documento.recurso_id)
        acreditacion = acreditacion_actual(documento)
        documento.resumen_interfaz = resumen_de_entrega(documento)
        filas.append({
            'documento': documento,
            'meta': _meta_de(documento),
            'enviado': enviado,
            'recibido': documento.recibido_en is not None,
            'evaluado': documento.evaluacion is not None,
            'cumple': None if acreditacion['nota_pendiente_correspondencia'] else documento.cumple,
            'nota_registrada': acreditacion['nota_registrada'],
            'nota_acreditable': acreditacion['nota_acreditable'],
            'correspondencia_pendiente': acreditacion['correspondencia_pendiente'],
            'nota_pendiente_correspondencia': acreditacion['nota_pendiente_correspondencia'],
            'tarde': documento.entregado_tarde,
            # Archivado y sin validar: la Dirección lo da por recibido y lo califica.
            'recibible': archivado and not enviado and (
                not documento.firma_pendiente),
            'evaluable': enviado and archivado,
            # Venció sin entregarse y la unidad lo pidió: falta que la Dirección abra la entrega.
            'ultimatable': (not enviado and documento.vencido and not documento.ultimatum_hasta
                            and not documento.prorroga_activa and not documento.correccion_hasta),
            'habilitable': (not enviado and (documento.ultimatum_hasta or documento.correccion_hasta)
                            and documento.plazo_entrega and documento.plazo_entrega < timezone.now()
                            and documento.solicitud_reapertura_pendiente
                            and (not documento.prorroga_activa or documento.correccion_hasta)
                            and not documento.correccion_abierta),
            'rastro': _rastro(documento),
            'observacion': (documento.evaluacion_observacion or documento.evaluacion_debilidades
                            or documento.observacion or documento.tardanza_motivo or ''),
        })
    return sorted(filas, key=lambda f: (f['documento'].exigido.carpeta != 'planeacion',
                                        f['documento'].exigido.orden, f['documento'].corte))


def _nivel_evaluado(documentos, hoy):
    """Desempeño del cierre acreditado; los trámites no son una nota de la unidad."""
    minimo = minimo_vigente()
    detalle = []
    from apps.documentos.presentation.progreso_general import evaluacion_operativa

    for documento in completar_acreditacion_actual(completar_controles_de_lectura(documentos)):
        if (documento.exigido.es_anexo or not documento.exigible
                or documento.exigido.codigo not in ('PLANIFICACION', 'INFORME-SEMESTRAL')):
            continue
        acreditacion = acreditacion_actual(documento)
        detalle.append(dict(documento=documento, **acreditacion))
    operativo = evaluacion_operativa(detalle, minimo)
    pendientes = sum(f['nota_pendiente_correspondencia'] for f in detalle)
    return {'total': operativo['nota'], 'total_registrado': operativo['nota_registrada'],
            'cumple': False if operativo['no_compensable'] else None if operativo['pendiente'] else True,
            'minimo': minimo, 'evaluacion_operativa': operativo,
            'calificados': sum(not f['pendiente'] for f in operativo['cierres']),
            'pendientes_correspondencia': pendientes}


def _entregas_firmadas(documentos, corte, hoy):
    """{'PLANIFICACION': fila, 'INFORME-SEMESTRAL': fila, 'unicos': [filas]} del período pedido."""
    firmados = {}
    unicos = []
    for documento in documentos:
        if documento.exigido.es_anexo:
            continue
        documento.semaforo_actual = documento.semaforo(hoy)
        documento.nombre_semaforo = NOMBRES_SEMAFORO[documento.semaforo_actual]
        documento.etapa_actual = documento.etapa(hoy)
        documento.nombre_etapa = NOMBRES_ETAPA[documento.etapa_actual]
        if documento.exigido.periodicidad in ('unica', 'anual'):
            unicos.append(documento)
        elif not corte or documento.corte == corte:
            firmados.setdefault(documento.exigido.codigo, []).append(documento)
    return {
        'planificacion': firmados.get('PLANIFICACION', []),
        'informe': firmados.get('INFORME-SEMESTRAL', []),
        'unicos': unicos,
    }


def _semaforo_de_unidad(cifras):
    if cifras['vencidos'] or cifras['observados'] or cifras['en_mejora']:
        return 'incumple'
    if cifras['por_validar'] or cifras['pendientes']:
        return 'en_riesgo'
    return 'al_dia'


def incumplimientos(documentos, hoy=None):
    """Lo que la unidad debía haber entregado y no entregó, en orden de gravedad."""
    hoy = hoy or timezone.localdate()
    filas = []
    for documento in documentos:
        # Un anexo no se le reclama a nadie: se exige el documento que lo lleva.
        if documento.exigido.es_anexo:
            continue
        estado = documento.semaforo(hoy)
        if documento.cumple is False:
            filas.append({
                'documento': documento, 'estado': 'evaluado' if es_calificable(documento.exigido) else 'vencido',
                'etiqueta': (f'Evaluado en {documento.evaluacion} %' if es_calificable(documento.exigido)
                             else 'No entregado dentro del plazo'),
                'dias': 0,
                'motivo': ' · '.join(p for p in (
                    documento.evaluacion_observacion, documento.evaluacion_debilidades,
                    f'Recomendación: {documento.evaluacion_recomendaciones}'
                    if documento.evaluacion_recomendaciones else '') if p)
                or 'No alcanzó el mínimo de cumplimiento.',
            })
            continue
        if estado not in ('vencido', 'observado'):
            continue
        filas.append({
            'documento': documento,
            'estado': estado,
            'etiqueta': NOMBRES_SEMAFORO[estado],
            'dias': (hoy - documento.vence_el).days if documento.vence_el else None,
            'motivo': documento.observacion or (
                'No se archivó ni se cargó dentro de su plazo.' if estado == 'vencido'
                else 'Devuelto con observaciones sin corregir.'),
        })
    return sorted(filas, key=lambda f: (f['estado'] != 'vencido', -(f['dias'] or 0)))


def _en_el_tramo(documento, desde, hasta):
    """Cae dentro del tramo pedido a mano.

    Se mira por su plazo, que es la fecha que la unidad tiene que cumplir. Lo
    que no tiene plazo —la resolución de creación, el protocolo— se exige
    siempre y entra en cualquier tramo.
    """
    if documento.vence_el is None:
        return True
    if desde and documento.vence_el < desde:
        return False
    if hasta and documento.vence_el > hasta:
        return False
    return True


@politica_consistente
def cumplimiento_de_unidad(unidad, anio, corte='', hoy=None, desde=None, hasta=None, *, documentos=None, cortes=None):
    """Una fila con el cumplimiento de la unidad en el período pedido.

    Por omisión el recorte es el del período; con un tramo propio —desde y
    hasta— se deja solo lo que vence dentro de esas fechas, que es como se pide
    un reporte de un mes o de una semana concretos.
    """
    hoy = hoy or timezone.localdate()
    # El mismo recorte que ve la unidad en su pantalla: si aquí contara otra
    # cosa, la Dirección y la unidad discutirían cifras distintas.
    documentos = del_periodo(documentos if documentos is not None else leer_expediente(unidad, anio, hoy),
                            corte, cortes if cortes is not None else cortes_del_anio(anio))
    if desde or hasta:
        documentos = [d for d in documentos if _en_el_tramo(d, desde, hasta)]
    documentos = completar_controles_de_lectura(documentos)
    cifras = resumen(documentos, hoy)
    faltantes = incumplimientos(documentos, hoy)
    nivel = _nivel_evaluado(documentos, hoy)
    semaforo = _semaforo_de_unidad(cifras)
    if semaforo == 'al_dia' and nivel['pendientes_correspondencia']:
        semaforo = 'en_riesgo'
    matriz = _matriz(documentos, hoy)
    anexos = anexos_de_seguimiento(documentos, hoy)
    return {
        'unidad': unidad,
        'es_laboratorio': unidad.dependencia == 'laboratorios' or unidad.codigo_base == 'laboratorios',
        'documentos': documentos,
        'automatizacion_resumen': resumen_controles_de_lectura(documentos),
        'incumplimientos': faltantes,
        'semaforo': semaforo,
        'etiqueta': SEMAFOROS_UNIDAD[semaforo][0],
        'motivo': SEMAFOROS_UNIDAD[semaforo][1],
        'por_validar_detalle': [d for d in documentos if d.semaforo(hoy) == 'por_validar'],
        # Las dos firmas del período y lo de una sola vez, para leerlas de un vistazo.
        'entregas': _entregas_firmadas(documentos, corte, hoy),
        'nivel': nivel,
        'progreso_general': progreso_general(documentos),
        # Lo que la unidad ya envió, firmado: la Dirección lo abre y lo evalúa aquí
        # mismo, sin entrar a la consola de la unidad.
        'matriz': matriz,
        'categorias_matriz': categorias_de_matriz(matriz),
        'anexos_seguimiento': anexos,
        'anexos_seguimiento_otros': [a for a in anexos if not a['es_soporte_planificacion']],
        'url': (reverse('gestion_expediente_unidad', args=[unidad.slug])
                + f'?anio={anio}&corte={corte}'),
        **cifras,
    }


def totales_de(filas):
    """Las cifras de un conjunto de unidades: sirven al total y a cada tipo por igual.

    El indicador institucional —cuántas unidades alcanzan el mínimo de la
    política— se lee igual para todas las unidades que para un solo tipo, así
    que se calcula en un solo sitio.
    """
    campos = ('total', 'validados', 'por_validar', 'vencidos', 'observados', 'pendientes',
              'no_abiertos', 'no_aplican', 'automaticos')
    totales = {campo: sum(fila[campo] for fila in filas) for campo in campos}
    totales['unidades'] = len(filas)
    totales['completo'] = (
        round(100 * totales['validados'] / totales['total']) if totales['total'] else 100)
    niveles = [fila['nivel']['total'] for fila in filas if fila['nivel']['total'] is not None]
    totales['minimo'] = minimo_vigente()
    totales['evaluadas'] = len(niveles)
    totales['cumplen_minimo'] = sum(1 for fila in filas if fila['nivel']['cumple'] is True)
    totales['pendientes_correspondencia'] = sum(
        1 for fila in filas if fila['nivel'].get('pendientes_correspondencia'))
    totales['bajo_minimo'] = sum(1 for fila in filas if fila['nivel']['cumple'] is False)
    # Sin calificar es lo que espera decisión, no lo que puntúa cero por vencimiento:
    # una unidad con todo vencido ya tiene nivel, pero nadie calificó nada suyo.
    totales['sin_evaluar'] = sum(1 for fila in filas if not fila['nivel']['calificados'])
    totales['indicador'] = (round(100 * totales['cumplen_minimo'] / totales['evaluadas'])
                            if totales['evaluadas'] else None)
    totales['nivel_medio'] = round(sum(niveles) / len(niveles)) if niveles else None
    totales['tardias'] = sum(1 for fila in filas for casilla in fila['matriz'] if casilla['tarde'])
    totales['incumplen'] = sum(1 for fila in filas if fila['semaforo'] == 'incumple')
    totales['en_riesgo'] = sum(1 for fila in filas if fila['semaforo'] == 'en_riesgo')
    totales['al_dia'] = sum(1 for fila in filas if fila['semaforo'] == 'al_dia')
    totales['automatizacion_resumen'] = {clave: sum(
        fila.get('automatizacion_resumen', {}).get(clave, 0) for fila in filas)
        for clave in ('total', 'automatico', 'revision', 'bloqueado', 'sin_archivo', 'sin_analizar',
                      'pendientes_direccion', 'pendientes_unidad', 'revisados_humano')}
    return totales


@politica_consistente
def cumplimiento_por_periodo(anio, corte='', usuario=None, dependencias=None, hoy=None,
                             desde=None, hasta=None, solo_unidad=''):
    """Filas por unidad y los totales, para el tablero de la Dirección.

    El alcance se acota fuera: un tipo de unidad, una unidad concreta o un
    tramo de fechas. Sin nada de eso, es el consolidado de todas.
    """
    hoy = hoy or timezone.localdate()
    unidades = unidades_auditadas(usuario, dependencias)
    if solo_unidad:
        unidades = unidades.filter(slug=solo_unidad)
    unidades = list(unidades)
    cortes = cortes_del_anio(anio)
    documentos = leer_expedientes(unidades, anio, hoy, cortes=cortes)
    completar_controles_de_lectura([d for lista in documentos.values() for d in lista])
    filas = [
        cumplimiento_de_unidad(unidad, anio, corte, hoy, desde, hasta,
                               documentos=documentos[unidad.pk], cortes=cortes)
        for unidad in unidades
    ]
    if solo_unidad:
        from .progreso_documento import completar_avance_de_unidad
        for fila in filas:
            completar_avance_de_unidad(fila['unidad'], anio, fila['documentos'], hoy=hoy)
            # La barra usa las mismas metas ya precargadas que las filas del
            # detalle; el consolidado no recalcula las fuentes de cada unidad.
            fila['progreso_general'] = progreso_general(fila['documentos'])
    totales = totales_de(filas)
    orden = {'incumple': 0, 'en_riesgo': 1, 'al_dia': 2}
    filas.sort(key=lambda fila: (orden[fila['semaforo']], -fila['vencidos'], fila['unidad'].nombre))
    return filas, totales


def grupos_por_tipo(filas):
    """Las unidades repartidas por tipología, cada grupo con su propio indicador.

    Un laboratorio y una planta piloto no se comparan entre sí: se leen dentro
    de su tipo, y el tablero se recorre tipo por tipo en lugar de una lista
    larga donde todo se mezcla.
    """
    grupos = []
    restantes = list(filas)
    tipos = tipos_auditados()
    codigos = [codigo for codigo, _ in tipos]
    for codigo, nombre in tipos:
        del_tipo = [fila for fila in restantes if fila['unidad'].dependencia == codigo]
        if not del_tipo:
            continue
        grupos.append({
            'codigo': codigo, 'nombre': nombre,
            'filas': del_tipo, 'totales': totales_de(del_tipo),
        })
    # Una unidad de un tipo que dejó de auditarse no se pierde de vista.
    sueltas = [fila for fila in restantes
               if fila['unidad'].dependencia not in codigos]
    if sueltas:
        grupos.append({'codigo': 'otras', 'nombre': 'Otras unidades',
                       'filas': sueltas, 'totales': totales_de(sueltas)})
    return grupos


def ventana_del_periodo(anio, corte):
    """(inicio, fin) del período, para encabezar el reporte."""
    cortes = cortes_del_anio(anio)
    if corte and corte in cortes:
        return cortes[corte]
    return date(anio, 1, 1), date(anio, 12, 31)


def preparar_vigencias_exportacion(documentos):
    """Precarga decisiones guardadas, sin abrir archivos ni recalcular controles."""
    from apps.documentos.presentation.conformidad_permanente import es_permanente, completar_aprobaciones

    pendientes = [d for d in documentos if getattr(d, 'exigido', None) is not None
        and es_permanente(d) and not hasattr(d, 'aprobacion_permanente')]
    if pendientes:
        completar_aprobaciones(pendientes)


def vigencia_exportada(documento):
    """La aprobación permanente se muestra como vigencia, nunca como una nota."""
    from apps.documentos.presentation.conformidad_permanente import es_permanente

    if getattr(documento, 'exigido', None) is None or not es_permanente(documento):
        return None
    aprobacion = getattr(documento, 'aprobacion_permanente', {}) or {}
    if aprobacion.get('vigente'):
        return 'Vigente'
    if aprobacion.get('revocada') or documento.estado == 'observado':
        return 'Observado'
    return 'Pendiente de aprobación'


def _resumen_firmas(documentos):
    """Cómo se lee una firma del período en el consolidado: estado y, si la hay, su nota."""
    if not documentos:
        return '—'
    documentos = list(documentos)
    preparar_vigencias_exportacion(documentos)
    from .conformidad_lectura import completar_conformidades, lectura_conformidad
    completar_controles_de_lectura(documentos)
    completar_conformidades(documentos)
    partes = []
    for documento in documentos:
        vigencia = vigencia_exportada(documento)
        if vigencia:
            partes.append(f'{vigencia} · aprobación única')
            continue
        texto = f'{documento.corte} · {documento.nombre_semaforo}' if documento.corte else documento.nombre_semaforo
        if documento.entregado_tarde:
            texto += ' · fuera de plazo'
        if documento.recibido_en:
            texto += ' · recibido por la Dirección'
        if getattr(getattr(documento, 'exigido', None), 'codigo', '') in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            conformidad = lectura_conformidad(documento)
            texto += ' · ' + conformidad['etiqueta']
            if conformidad['historica']:
                texto += ' · revisión histórica conservada'
        elif es_calificable(documento.exigido) and documento.evaluacion is not None:
            texto += f' · {documento.nota} %'
        elif getattr(documento, 'cumple', None):
            texto += ' · aceptado'
        partes.append(texto)
    return '\n'.join(partes)


def resultado_cierre_exportado(fila):
    """La exportación distingue un cierre pendiente de un resultado insuficiente."""
    nivel = fila.get('nivel') or {}
    if nivel.get('total') is None:
        return 'Pendiente de cierre acreditado'
    estado = ('cumple' if nivel.get('cumple') is True else
              'no cumple' if nivel.get('cumple') is False else 'por verificar')
    return f'{nivel["total"]} % · {estado}'


def pdf_de_cumplimiento(filas, totales, anio, corte, *, titulo='Cumplimiento del expediente de calidad',
                        alcance='todas las unidades', tramo=None, bandeja=''):
    """El consolidado con el marco institucional, igual que el resto de documentos.

    Se lee tipo por tipo —laboratorios, plantas piloto, centros experimentales,
    observatorios—, porque unidades de tipos distintos no se comparan entre sí.
    El encabezado dice siempre qué alcance y qué tramo se pidió.
    """
    from io import BytesIO
    from xml.sax.saxutils import escape

    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from apps.core.presentation.identidad import identidad_actual

    from apps.core.presentation.pdf_institucional import marco_institucional

    preparar_vigencias_exportacion(
        [c['documento'] for fila in filas for c in fila.get('matriz', ())]
        + [f['documento'] for fila in filas for f in fila.get('incumplimientos', ())]
    )
    inicio, fin = ventana_del_periodo(anio, corte)
    if tramo:
        inicio, fin = tramo[0] or inicio, tramo[1] or fin
    periodo = f'{anio}-{corte}' if corte else f'Año {anio}'
    dibujar, CanvasNumerado, medidas = marco_institucional(
        formato='SEGUIMIENTO DEL EXPEDIENTE DE CALIDAD',
        metadatos=(
            f'Período: {periodo}',
            f'Tramo: {inicio:%d/%m/%Y} – {fin:%d/%m/%Y}',
            f'Alcance: {alcance} ({totales["unidades"]})',
            f'Emitido: {timezone.localdate():%d/%m/%Y}',
        ),
        pie='Dirección · seguimiento del expediente',
        apaisado=True,
    )
    tinta, ancho = medidas['colores'], medidas['ancho_util']
    base = hoja_de_estilos()
    estilos = {
        'titulo': ParagraphStyle('t', parent=base['Title'], fontName=fuentes_documento()[1], fontSize=13,
                                 leading=16, textColor=tinta['primario'], alignment=1, spaceAfter=2),
        'sub': ParagraphStyle('s', parent=base['BodyText'], fontSize=8, leading=11,
                              textColor=tinta['tenue'], alignment=1),
        'celda': ParagraphStyle('c', parent=base['BodyText'], fontSize=7.4, leading=9.4),
        'celda_b': ParagraphStyle('cb', parent=base['BodyText'], fontName=fuentes_documento()[1],
                                  fontSize=7.4, leading=9.4, textColor=tinta['oscuro']),
        'seccion': ParagraphStyle('h', parent=base['Heading2'], fontName=fuentes_documento()[1], fontSize=10,
                                  leading=13, textColor='white', spaceBefore=0, spaceAfter=0),
        'vacio': ParagraphStyle('v', parent=base['BodyText'], fontName=fuentes_documento()[0],
                                fontSize=8.2, leading=11, textColor=tinta['tenue']),
    }

    def banda(texto):
        tabla = Table([[Paragraph(escape(texto.upper()), estilos['seccion'])]], splitInRow=1, colWidths=[ancho])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), tinta['primario']),
            ('LINEBELOW', (0, 0), (-1, -1), 1.5, tinta['acento']),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        tabla.keepWithNext = 1
        return tabla

    def tabla(cabecera, datos, anchos):
        cuerpo = [[Paragraph(escape(str(c)), estilos['celda_b']) for c in cabecera]]
        cuerpo += [[Paragraph(escape(str(c)), estilos['celda']) for c in fila] for fila in datos]
        t = Table(cuerpo, splitInRow=1, colWidths=anchos, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), tinta['suave']),
            ('LINEBELOW', (0, 0), (-1, 0), 0.8, tinta['primario']),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, tinta['linea']),
            ('BOX', (0, 0), (-1, -1), 0.5, tinta['linea']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    historia = [
        Paragraph(escape(titulo), estilos['titulo']),
        Paragraph(escape(f'{periodo} · {totales["cumplen_minimo"]} de {totales["evaluadas"]} unidad(es) '
                         f'con resultado alcanzan el {totales["minimo"]} % · '
                         f'{totales["completo"]} % de las entregas recibidas · '
                         f'{totales["tardias"]} fuera de plazo'), estilos['sub']),
        Spacer(1, 4 * mm),
        Paragraph('La puntuación corresponde exclusivamente al informe de cierre acreditado y a sus metas, '
            'con planificación conforme del mismo semestre. Resolución y protocolo se controlan por vigencia; '
            'el plan de compras gestiona necesidades. Estos documentos no aportan puntos de desempeño.',
            estilos['celda']),
        Spacer(1, 2 * mm),
    ]
    nombre_bandeja = {'excepciones': 'Pendientes de Dirección', 'unidad': 'Pendientes de la unidad',
        'automatico': 'Control automático correcto', 'sin_analizar': 'Sin analizar o desactualizados'}.get(bandeja, '')
    if nombre_bandeja:
        historia.extend([Paragraph(escape(
            f'Bandeja: {nombre_bandeja}. Se incluyen todas las unidades y documentos que coinciden con el filtro, '
            'sin el límite de paginación de la pantalla. Los totales generales anteriores corresponden a todo '
            'el alcance consultado; los porcentajes y niveles de cada unidad conservan todas sus entregas previstas.'),
            estilos['celda']), Spacer(1, 4 * mm)])
    # Tipo por tipo: cada grupo con su indicador antes de su tabla. El nombre de la
    # unidad se queda con lo que sobra del ancho útil, para que la tabla no se salga.
    columnas = (40, 22, 32, 32, 26, 26)
    grupos = grupos_por_tipo(filas)
    for numero, grupo in enumerate(grupos, start=1):
        suyos = grupo['totales']
        historia.append(banda(f'{numero}. {grupo["nombre"]}'))
        historia.append(Spacer(1, 1.5 * mm))
        historia.append(Paragraph(escape(
            f'{suyos["cumplen_minimo"]} de {suyos["evaluadas"]} unidad(es) con resultado alcanzan el '
            f'{suyos["minimo"]} % · {suyos["completo"]} % de las entregas recibidas · '
            f'{suyos["incumplen"]} incumplen'), estilos['celda']))
        historia.append(Spacer(1, 1.5 * mm))
        historia.append(tabla(
            ['Unidad', 'Adscrita a', 'Estado', 'Planificación · conformidad documental', 'Informe de cierre',
             'Recibidas', 'Resultado del cierre'],
            [[fila['unidad'].nombre, str(fila['unidad'].adscrita_a or '—'), fila['etiqueta'],
              _resumen_firmas(fila['entregas']['planificacion']),
              _resumen_firmas(fila['entregas']['informe']),
              f'{fila["validados"]}/{fila["total"]} · {fila["completo"]} %',
              resultado_cierre_exportado(fila)]
             for fila in grupo['filas']],
            [ancho - sum(columnas) * mm] + [c * mm for c in columnas]))
        if nombre_bandeja:
            historia.append(Spacer(1, 2 * mm))
            historia.append(Paragraph(escape(f'Documentos de la bandeja: {nombre_bandeja}'), estilos['celda_b']))
            historia.append(tabla(
                ['Unidad', 'Documento', 'Período', 'Estado documental', 'Plazo vigente'],
                [[fila['unidad'].nombre, documento.nombre_documental,
                  documento.etiqueta_corte + (' · Anexo sin aporte independiente' if documento.exigido.es_anexo else ''),
                  (f'{vigencia_exportada(documento)} · aprobación única'
                   if vigencia_exportada(documento) else documento.nombre_semaforo),
                  _fecha(documento.plazo_entrega) or 'Sin fecha asignada']
                 for fila in grupo['filas'] for documento in documentos_de_bandeja(fila)],
                [52 * mm, ancho - 150 * mm, 24 * mm, 38 * mm, 36 * mm]))
        historia.append(Spacer(1, 4 * mm))
    if not grupos:
        historia.append(Paragraph('No hay documentos con ese control dentro del alcance seleccionado.'
            if nombre_bandeja else 'No hay unidades que auditar con este alcance.', estilos['vacio']))
        historia.append(Spacer(1, 4 * mm))
    historia.append(banda(f'{len(grupos) + 1}. Entregas incumplidas'))
    separacion_cabecera = Spacer(1, 2 * mm)
    separacion_cabecera.keepWithNext = 1
    historia.append(separacion_cabecera)
    faltantes = [
        [fila['unidad'].nombre, falta['documento'].nombre_documental,
         falta['documento'].etiqueta_corte, vigencia_exportada(falta['documento']) or falta['etiqueta'],
         f'{falta["documento"].vence_el:%d/%m/%Y}' if falta['documento'].vence_el else '—',
         f'{falta["dias"]} días' if falta['dias'] else '—', falta['motivo']]
        for fila in filas for falta in fila['incumplimientos']
        if not nombre_bandeja or falta['documento'].pk in {c['documento'].pk for c in fila['matriz']}
    ]
    if faltantes:
        historia.append(tabla(
            ['Unidad', 'Documento', 'Período', 'Estado', 'Venció', 'Atraso', 'Motivo'],
            faltantes,
            # El nombre del documento se queda con lo que sobra: así la tabla cabe justa.
            [42 * mm, ancho - (42 + 24 + 24 + 24 + 20 + 52) * mm,
             24 * mm, 24 * mm, 24 * mm, 20 * mm, 52 * mm]))
    else:
        historia.append(Paragraph('Ninguna entrega de esta bandeja tiene incumplimientos registrados.'
                                  if nombre_bandeja else 'Ninguna unidad tiene entregas vencidas ni observadas en el período.',
                                  estilos['vacio']))

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=medidas['pagesize'], leftMargin=medidas['margen'],
        rightMargin=medidas['margen'], topMargin=medidas['margen_superior'],
        bottomMargin=medidas['margen_inferior'],
        title=f'{titulo} {periodo}', author=identidad_actual()[1].nombre,
    )
    documento.build(historia, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=CanvasNumerado)
    return buffer.getvalue()
