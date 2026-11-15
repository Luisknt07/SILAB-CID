"""El expediente de calidad de una unidad: construirlo, generar, cargar, validar.

Un año de gestión tiene dos semestres naturales: enero–junio y julio–diciembre.
El calendario académico orienta la docencia, sin redefinir estos reportes.
Cada documento conserva el alcance con el que se preparó y los archivos ya
guardados mantienen sus fechas, versiones y resultados originales.
"""

from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from apps.core.identificadores import id_solicitado

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpRequest, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.core.models.periodos import PeriodoAcademico
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import (
    CARPETAS, NOMBRES_CARPETA, NOMBRES_ETAPA, es_calificable, minimo_vigente, politica_consistente,
)
from apps.recursos.models.recursos import FORMATOS_ADJUNTO_PERMITIDOS

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.presentation.expediente_redaccion import avance, obtener_redaccion, pdf_acciones_de_mejora, pdf_del_documento
from apps.gestion_unidades.presentation.permisos import es_receptor_de, puede_operar_modulo_unidad
from apps.documentos.presentation.expediente_operaciones import comando, recordar_archivo, recordar_extraccion
from apps.reservas.presentation.guia_firma_certificada import validar_pdf_firmado

MAXIMO_BYTES_CARGA = 25 * 1024 * 1024
# Capacidad interna: sólo el comando de conformidad puede registrar su
# equivalencia documental. No es un indicador ni un permiso enviable por POST.
_REGISTRO_CONFORMIDAD_PLAN = object()
# Solo el cierre calculado del informe semestral escribe su nota: ninguna petición ni formulario la fija a mano.
_REGISTRO_CIERRE = object()
ORDEN_SEMAFORO = ('vencido', 'observado', 'por_validar', 'por_vencer', 'a_tiempo', 'no_abierto',
                  'sin_plazo', 'validado', 'disponible', 'archivado', 'no_aplica')
NOMBRES_SEMAFORO = {
    'vencido': 'Vencido', 'observado': 'Observado', 'por_vencer': 'Vence pronto',
    'por_validar': 'Archivado, por validar', 'a_tiempo': 'A tiempo', 'no_abierto': 'Aún no se entrega',
    'sin_plazo': 'Sin plazo', 'validado': 'Validado y enviado',
    'disponible': 'Automático', 'archivado': 'Archivado', 'no_aplica': 'No aplica',
}

# En qué orden se lee una carpeta: primero lo que reclama una decisión, después
# lo que está en curso y al final lo cerrado. Antes salía por número de orden
# del catálogo y lo validado se mezclaba con lo vencido.
# -- tramos del año -------------------------------------------------------------

def cortes_del_anio(anio):
    """Semestres de gestión: A enero–junio y B julio–diciembre."""
    return {'A': (date(anio, 1, 1), date(anio, 6, 30)),
            'B': (date(anio, 7, 1), date(anio, 12, 31))}


def cortes_academicos_del_anio(anio):
    """Referencia docente publicada; nunca redefine el semestre de gestión."""
    cortes = {'A': (date(anio, 1, 1), date(anio, 6, 30)), 'B': (date(anio, 7, 1), date(anio, 12, 31))}
    periodos = (
        PeriodoAcademico.objects.operativos().publicados()
        .filter(anio_referencia=anio, ciclo__in=('A', 'B'), tipo='ordinario')
        .prefetch_related('versiones')
    )
    for periodo in periodos:
        version = next((v for v in periodo.versiones.all() if v.vigente), None)
        if version is not None:
            cortes[periodo.ciclo] = (version.fecha_inicio_clases, version.fecha_fin_periodo)
    return cortes


def rango_anual(cortes):
    return cortes['A'][0], cortes['B'][1]


def periodo_vigente(cortes, hoy):
    """El corte donde cae hoy; entre períodos, el último que ya empezó.

    Al cerrar A todavía se entregan sus informes, así que el expediente sigue
    abierto en A hasta que B empieza.
    """
    for clave in ('A', 'B'):
        if cortes[clave][0] <= hoy <= cortes[clave][1]:
            return clave
    empezados = [clave for clave in ('A', 'B') if cortes[clave][0] <= hoy]
    return empezados[-1] if empezados else 'A'


def del_periodo(documentos, corte, cortes):
    """Los documentos que se leen en ese corte; sin corte, el año entero.

    Lo semestral entra por su corte y lo mensual por el mes que cae dentro. Lo
    anual pertenece al año completo, así que se ve desde cualquiera de los dos
    períodos: es una sola fila, no una copia por semestre.
    """
    if not corte:
        return list(documentos)
    inicio, fin = cortes[corte]
    elegidos = []
    for documento in documentos:
        if documento.corte:
            if documento.corte == corte:
                elegidos.append(documento)
        elif documento.mes:
            if inicio <= date(documento.anio, documento.mes, 1) <= fin:
                elegidos.append(documento)
        else:
            elegidos.append(documento)
    return elegidos


def tramo_del_documento(documento, cortes=None):
    """Alcance conservado de la versión; las reformas no relabelan sus archivos."""
    if documento.tramo_inicio and documento.tramo_fin:
        return documento.tramo_inicio, documento.tramo_fin
    if documento.marco_periodo == 'academico_legacy':
        cortes = cortes_academicos_del_anio(documento.anio)
    else:
        cortes = cortes_del_anio(documento.anio)
    if documento.periodicidad_documental == 'anual':
        # Un anexo anual viaja con un período, pero lo que reporta es el año.
        return rango_anual(cortes)
    if documento.mes:
        inicio = date(documento.anio, documento.mes, 1)
        fin = date(documento.anio + (documento.mes == 12), documento.mes % 12 + 1, 1)
        return inicio, date.fromordinal(fin.toordinal() - 1)
    if documento.corte:
        return cortes[documento.corte]
    return rango_anual(cortes)


def instantanea_periodo(documento):
    inicio, fin = tramo_del_documento(documento)
    return dict(marco=documento.marco_periodo, inicio=inicio.isoformat(), fin=fin.isoformat())


def _exigir_cierre_concluido(documento):
    if documento.exigido.codigo == 'INFORME-SEMESTRAL' and documento.marco_periodo != 'academico_legacy':
        _, fin = tramo_del_documento(documento)
        if timezone.localdate() <= fin:
            raise ValidationError('El semestre de gestión aún no ha concluido. Puedes preparar y revisar '
                'el informe provisional, pero el envío definitivo se habilita después del cierre.')


# -- construir ------------------------------------------------------------------

def _tramos(exigido, anio, cortes, hoy, unidad=None):
    """Los (corte, mes, inicio, fin) que un documento exigido tiene en un año."""
    periodicidad = exigido.periodicidad_para(unidad)
    if periodicidad == 'anual' and exigido.es_anexo:
        # El anexo anual viaja con la planificación de A o con el informe de B.
        return [(exigido.corte_del_anexo_anual, None, *rango_anual(cortes))]
    if periodicidad == 'semestral':
        return [(clave, None, *cortes[clave]) for clave in ('A', 'B')]
    if periodicidad == 'mensual':
        ultimo_mes = hoy.month if anio == hoy.year else (12 if anio < hoy.year else 0)
        tramos = []
        for mes in range(1, ultimo_mes + 1):
            inicio = date(anio, mes, 1)
            fin = date.fromordinal(date(anio + (mes == 12), mes % 12 + 1, 1).toordinal() - 1)
            tramos.append(('', mes, inicio, fin))
        return tramos
    return [('', None, *rango_anual(cortes))]


@transaction.atomic
def construir_expediente(unidad, anio, hoy=None):
    """Materializa las filas del expediente del año y devuelve la lista completa."""
    hoy = hoy or timezone.localdate()
    Unidad.objects.select_for_update().get(pk=unidad.pk)
    cortes = cortes_del_anio(anio)
    asegurar_catalogo()
    from apps.documentos.presentation.perfil_unidades import base_de, documento_visible
    base = base_de(unidad)
    exigidos = [e for e in DocumentoExigido.objects.filter(activo=True)
                if e.aplica_a(unidad.dependencia, base=base)]
    for exigido in exigidos:
        for corte, mes, inicio, fin in _tramos(exigido, anio, cortes, hoy, unidad):
            vence_el = exigido.vence(inicio, fin)
            abre_el = exigido.abre(inicio, fin)
            documento, creado = DocumentoExpediente.objects.get_or_create(
                unidad=unidad, exigido=exigido, anio=anio, corte=corte, mes=mes,
                defaults={'vence_el': vence_el, 'abre_el': abre_el,
                    'tramo_inicio': inicio, 'tramo_fin': fin, 'marco_periodo': 'gestion_v1'},
            )
            if not creado and documento.marco_periodo != 'academico_legacy' and documento.estado == 'pendiente' and not documento.recurso_id and (
                    documento.vence_el != vence_el or documento.abre_el != abre_el):
                # Sólo una obligación nueva sin archivo sigue las reglas de
                # entrega actuales; el alcance y las ventanas legadas se conservan.
                DocumentoExpediente.objects.filter(pk=documento.pk).update(
                    vence_el=vence_el, abre_el=abre_el)
    documentos = list(
        DocumentoExpediente.objects.filter(unidad=unidad, anio=anio, exigido__activo=True)
        .select_related('exigido', 'recurso', 'cargado_por', 'validado_por', 'recibido_por',
                        'evaluado_por', 'tardanza_habilitada_por')
    )
    documentos = [d for d in documentos if documento_visible(d, unidad)]
    from apps.documentos.presentation.conformidad_permanente import completar_aprobaciones
    completar_aprobaciones(documentos)
    anteriores = _antecedentes_permanentes([unidad.pk], anio, documentos=documentos)
    for documento in documentos:
        if documento.exigido.periodicidad == 'unica':
            # También reconcilia años preparados antes de cargar la resolución.
            _heredar(documento, anteriores=anteriores)
    return documentos


def leer_expediente(unidad, anio, hoy=None):
    """Proyecta las obligaciones pendientes sin crear filas al consultar."""
    return leer_expedientes([unidad], anio, hoy)[unidad.pk]


def leer_expedientes(unidades, anio, hoy=None, *, cortes=None):
    """Carga un conjunto de expedientes sin repetir catálogo, calendario ni herencia."""
    from apps.core.presentation.tipologias import tipologias_actuales
    from apps.documentos.presentation.perfil_unidades import BASES_AUDITABLES, documento_visible

    unidades = list(unidades)
    if not unidades:
        return {}
    hoy = hoy or timezone.localdate()
    cortes = cortes if cortes is not None else cortes_del_anio(anio)
    ids = [unidad.pk for unidad in unidades]
    relaciones = ('unidad', 'exigido', 'exigido__anexo_de', 'recurso', 'cargado_por',
                  'validado_por', 'recibido_por', 'evaluado_por', 'tardanza_habilitada_por')
    por_unidad = defaultdict(list)
    for documento in DocumentoExpediente.objects.filter(
            unidad_id__in=ids, anio=anio, exigido__activo=True).select_related(*relaciones):
        if documento_visible(documento):
            por_unidad[documento.unidad_id].append(documento)
    anteriores = _antecedentes_permanentes(ids, anio, documentos=[d for filas in por_unidad.values() for d in filas])
    catalogo = list(DocumentoExigido.objects.filter(activo=True).select_related('anexo_de'))
    bases = ({t.codigo: t.base for t in tipologias_actuales()}
             if any(u.dependencia not in BASES_AUDITABLES for u in unidades) else {})
    for unidad in unidades:
        documentos = por_unidad[unidad.pk]
        existentes = {(d.exigido_id, d.corte, d.mes) for d in documentos}
        for exigido in catalogo:
            if not exigido.aplica_a(unidad.dependencia, base=bases.get(unidad.dependencia, unidad.dependencia)):
                continue
            for corte, mes, inicio, fin in _tramos(exigido, anio, cortes, hoy, unidad):
                if (exigido.pk, corte, mes) in existentes:
                    continue
                documento = DocumentoExpediente(
                    unidad=unidad, exigido=exigido, anio=anio, corte=corte, mes=mes,
                    abre_el=exigido.abre(inicio, fin), vence_el=exigido.vence(inicio, fin),
                    tramo_inicio=inicio, tramo_fin=fin, marco_periodo='gestion_v1')
                documentos.append(documento)
    from apps.documentos.presentation.conformidad_permanente import completar_aprobaciones
    todos = [d for filas in por_unidad.values() for d in filas]
    completar_aprobaciones(todos)
    for documento in todos:
        if documento.exigido.periodicidad == 'unica':
            # Una lectura proyecta la vigencia; nunca crea filas ni decisiones.
            _heredar(documento, guardar=False, anteriores=anteriores)
    from apps.documentos.presentation.expediente_interfaz import completar_fechas_envio
    completar_fechas_envio([d for filas in por_unidad.values() for d in filas])
    from apps.documentos.presentation.automatizacion_documental import completar_controles
    completar_controles([d for filas in por_unidad.values() for d in filas])
    from apps.documentos.presentation.expediente_archivos import completar_integridad_documental
    completar_integridad_documental([d for filas in por_unidad.values() for d in filas])
    return dict(por_unidad)


@transaction.atomic
def preparar_expediente(unidad, anio, usuario, request=None):
    if not puede_operar_modulo_unidad(usuario, unidad, 'reportes'):
        raise PermissionDenied
    documentos = construir_expediente(unidad, anio)
    registrar_auditoria(request, unidad=unidad, usuario=usuario, accion='crear', objeto=unidad,
                        descripcion=f'Preparó el expediente de calidad {anio}',
                        nuevos={'anio': anio, 'documentos': [d.pk for d in documentos]})
    return documentos


def anexos_del(documento):
    """Las filas anexas al documento firmado, en su mismo año y período."""
    if documento.exigido.es_anexo or documento.mes:
        return []
    from apps.documentos.presentation.perfil_unidades import documento_visible
    exigidos = list(documento.exigido.anexos.filter(activo=True))
    if not exigidos:
        return []
    filas = list(
        DocumentoExpediente.objects.filter(
            unidad=documento.unidad, anio=documento.anio, exigido__in=exigidos, mes__isnull=True)
        .select_related('exigido', 'recurso', 'validado_por')
    )
    # Cada anexo lleva el corte del período con el que viaja (el anual, solo uno):
    # basta con quedarse con los del mismo corte que el documento.
    return sorted(
        (f for f in filas if f.corte == documento.corte and documento_visible(f, documento.unidad)),
        key=lambda f: (f.exigido.carpeta, f.exigido.orden, f.exigido.codigo),
    )


@comando
def generar_anexos(documento, usuario, solo_faltantes=False):
    """Produce con lo registrado cada anexo del documento firmado que aún no esté cerrado."""
    if documento.estado == 'validado':
        raise ValidationError('Los anexos de una entrega enviada no se reemplazan.')
    for anexo in anexos_del(documento):
        if documento.exigido.codigo == 'INFORME-SEMESTRAL' and not solo_faltantes:
            anexo.estado = 'generado'
            anexo.save(update_fields=['estado'])
        elif anexo.estado == 'validado':
            continue
        if solo_faltantes and anexo.recurso_id:
            continue
        _generar(anexo, usuario)
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    if es_unidad_auditable(documento.unidad):
        from apps.documentos.presentation.automatizacion_documental import procesar_expediente
        procesar_expediente(anexos_del(documento), usuario=usuario)


@comando
def validar_anexo(anexo, usuario):
    """La unidad revisa el anexo y lo da por bueno: la información es correcta y no está vacía por error.

    Un anexo lo produce el sistema, pero puede salir vacío o con datos que no
    son; por eso quien administra la unidad lo abre, lo revisa y lo valida uno
    por uno antes de enviar el documento que lo lleva.
    """
    if not anexo.exigido.es_anexo:
        raise ValidationError('Esto no es un anexo: se valida como documento.')
    from apps.documentos.presentation.expediente_operaciones import entrega_del_anexo
    if entrega_del_anexo(anexo).estado == 'validado':
        raise ValidationError('La entrega ya fue enviada; Dirección debe devolverla antes de corregir sus anexos.')
    from .integridad_anexos import exigir_archivo_anexo
    exigir_archivo_anexo(anexo)
    if anexo.estado == 'validado':
        return
    anexo.estado = 'validado'
    anexo.validado_en = timezone.now()
    anexo.validado_por = usuario
    anexo.save(update_fields=['estado', 'validado_en', 'validado_por', 'actualizado_en'])


@comando
def rectificar_anexo(anexo, usuario, version, *, actualizar=False):
    """Retira la revisión o produce otra versión sin alterar lo enviado ni el PDF anterior."""
    from apps.documentos.presentation.expediente_operaciones import entrega_del_anexo

    entrega = entrega_del_anexo(anexo)
    if entrega.estado == 'validado':
        raise ValidationError('La entrega ya fue enviada; Dirección debe devolverla antes de corregir sus anexos.')
    if not anexo.recurso_id or str(anexo.version) != str(version):
        raise ValidationError('El anexo cambió. Revisa la versión vigente antes de rectificarlo.')
    anexo.estado = 'generado'
    anexo.validado_en = None
    anexo.validado_por = None
    anexo.save(update_fields=['estado', 'validado_en', 'validado_por', 'actualizado_en'])
    if actualizar:
        _generar(anexo, usuario)


def anexos_sin_revisar(documento):
    return [a for a in anexos_del(documento) if a.estado != 'validado']


def cerrar_anexos(documento, usuario):
    """Los anexos quedan validados con el documento que los lleva."""
    ahora = timezone.now()
    from .integridad_anexos import exigir_archivo_anexo
    for anexo in anexos_del(documento):
        if anexo.estado == 'no_aplica':
            continue
        exigir_archivo_anexo(anexo)
        anexo.estado = 'validado'
        anexo.validado_en = ahora
        anexo.validado_por = usuario
        anexo.save(update_fields=['estado', 'validado_en', 'validado_por', 'actualizado_en'])


def reabrir_anexos(documento):
    """Devuelto el documento, sus anexos vuelven a poder regenerarse."""
    DocumentoExpediente.objects.filter(
        pk__in=[a.pk for a in anexos_del(documento) if a.estado == 'validado']
    ).update(estado='generado', validado_en=None, validado_por=None)


def _antecedentes_permanentes(unidades, anio, *, documentos=()):
    """Última revisión real por obligación; una retirada nunca salta al archivo previo.

    Las filas vacías creadas al preparar un año no son revisiones. En cambio una
    versión retirada u observada sigue siendo el último antecedente y bloquea la
    herencia: filtrar primero por estados aceptados resucitaría versiones viejas.
    """
    anteriores, por_id, por_anio = {}, {}, {}
    candidatos = list(DocumentoExpediente.objects.filter(
        unidad_id__in=unidades, anio__lt=anio, exigido__periodicidad='unica',
    ).filter(Q(version__gt=0) | Q(recurso__isnull=False) | Q(estado='observado')).select_related(
        'unidad', 'exigido', 'recurso', 'cargado_por', 'validado_por', 'recibido_por',
    ).order_by('-version', '-actualizado_en', '-anio', '-pk'))
    for anterior in candidatos:
        anteriores.setdefault((anterior.unidad_id, anterior.exigido_id), anterior)
        por_id[anterior.pk] = anterior
        por_anio[(anterior.unidad_id, anterior.exigido_id, anterior.anio)] = anterior
    for anterior in anteriores.values():
        anterior._herencia_origenes_por_id = por_id
        anterior._herencia_origenes_por_anio = por_anio
    # Sólo el caso de una copia cargada antes de aceptar su original necesita
    # probar su origen. La consulta es una por lote, nunca una por documento.
    documentos = list(documentos)
    if any(d.estado == 'cargado' and d.recurso_id and d.observacion.startswith('Heredado del año ')
           for d in documentos):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        sujetos = {d.pk: d for d in (*candidatos, *documentos) if d.pk}
        for d in sujetos.values():
            d._herencia_cargas_propias = []
        for registro in RegistroAuditoriaUnidad.objects.filter(
                unidad_id__in=unidades, entidad='documentos.DocumentoExpediente',
                objeto_id__in=[str(pk) for pk in sujetos],
                descripcion__startswith='cargar_documento:').only(
                    'objeto_id', 'unidad_id', 'usuario_id', 'datos_nuevos'):
            destino = sujetos.get(int(registro.objeto_id))
            if destino and registro.unidad_id == destino.unidad_id:
                destino._herencia_cargas_propias.append(registro)
    return anteriores


def _reconciliar_herencia_cargada(documento, anterior, *, guardar):
    """Aceptación original posterior a preparar otro año; conserva una sola decisión."""
    from apps.documentos.presentation.conformidad_permanente import aprobacion_vigente
    aprobacion = documento.aprobacion_permanente
    if (documento.estado != 'cargado' or not documento.recurso_id or not aprobacion.get('aprobada')
            or documento.correccion_hasta or documento.validado_en or documento.validado_por_id
            or documento.recibido_en or documento.recibido_por_id
            or getattr(documento, '_herencia_cargas_propias', None) != []):
        return
    origen = getattr(anterior, '_herencia_origenes_por_id', {}).get(aprobacion.get('documento_id'))
    if origen is None:
        return
    fuentes = getattr(anterior, '_herencia_origenes_por_anio', {})
    referencia = next((d for (unidad, exigido, _anio), d in fuentes.items()
                      if unidad == documento.unidad_id and exigido == documento.exigido_id
                      and documento.observacion == f'Heredado del año {d.anio}.'), None)
    if referencia is None or referencia.anio >= documento.anio:
        return
    identidad = (documento.unidad_id, documento.exigido_id, documento.recurso_id, documento.version)
    if any((d.unidad_id, d.exigido_id, d.recurso_id, d.version) != identidad
           for d in (origen, referencia)):
        return
    if (documento.cargado_en != origen.cargado_en or documento.cargado_por_id != origen.cargado_por_id
            or documento.recurso.hash_sha256 != aprobacion.get('sha256')):
        return
    cargas = getattr(origen, '_herencia_cargas_propias', ())
    if not any(isinstance(r.datos_nuevos, dict) and r.usuario_id == origen.cargado_por_id
               and r.datos_nuevos.get('recurso_id') == origen.recurso_id
               and r.datos_nuevos.get('version') == origen.version for r in cargas):
        return
    origen._aprobacion_permanente_registro = documento._aprobacion_permanente_registro
    origen._aprobacion_permanente_control_origen = getattr(
        documento, '_aprobacion_permanente_control_origen', None)
    if not aprobacion_vigente(origen):
        return
    documento.estado = 'validado'
    documento.firma_verificada = origen.firma_verificada
    for campo in ('entregado_en', 'validado_en', 'validado_por', 'recibido_en', 'recibido_por'):
        setattr(documento, campo, getattr(origen, campo))
    aprobacion_vigente(documento)
    if guardar:
        documento.save(update_fields=['estado', 'firma_verificada', 'entregado_en', 'validado_en',
            'validado_por', 'recibido_en', 'recibido_por', 'actualizado_en'])


def _heredar(documento, guardar=True, *, anteriores=None):
    """Proyecta el archivo permanente sin fabricar otra revisión o calificación."""
    # Sólo se completan marcadores vacíos. No se pisa un archivo, una retirada,
    # una observación local ni una revisión que deba decidir la autoridad.
    if documento.exigido.periodicidad != 'unica':
        return
    from apps.documentos.presentation.conformidad_permanente import completar_aprobaciones
    if not hasattr(documento, 'aprobacion_permanente'):
        completar_aprobaciones([documento])
    if (getattr(documento, 'aprobacion_permanente', None) or {}).get('revocada'):
        return
    if anteriores is None:
        anteriores = _antecedentes_permanentes([documento.unidad_id], documento.anio, documentos=[documento])
    anterior = anteriores.get((documento.unidad_id, documento.exigido_id))
    if documento.recurso_id:
        _reconciliar_herencia_cargada(documento, anterior, guardar=guardar)
        return
    if documento.version or documento.estado != 'pendiente' or documento.observacion:
        return
    if (anterior is None or anterior.estado not in ('cargado', 'validado')
            or not anterior.recurso_id or not anterior.recurso.activo
            or anterior.recurso.estado != 'vigente'
            or anterior.recurso.unidad_id != documento.unidad_id):
        return
    documento.recurso = anterior.recurso
    documento.estado = anterior.estado
    documento.version = anterior.version
    documento.firma_verificada = anterior.firma_verificada
    documento.entregado_en = anterior.entregado_en
    documento.cargado_en, documento.cargado_por = anterior.cargado_en, anterior.cargado_por
    documento.validado_en, documento.validado_por = anterior.validado_en, anterior.validado_por
    documento.observacion = f'Heredado del año {anterior.anio}.'
    from apps.documentos.presentation.conformidad_permanente import aprobacion_vigente
    aprobacion_vigente(documento)  # Recalcula desde la decisión precargada, sin otra consulta.
    if guardar:
        documento.save()


def _categorias_de_reporte(unidad):
    """Las categorías del Centro de reportes, sin atarse a él al importar."""
    from apps.gestion_unidades.presentation.gestion_reportes import categorias_para

    return {codigo for codigo, _nombre in categorias_para(unidad)}


@politica_consistente
def resumen(documentos, hoy=None):
    """Cuenta todo lo que el expediente pide; solo queda fuera lo que no aplica.

    Que el sistema produzca un documento no lo da por entregado: hay que
    archivarlo y validarlo dentro de su ventana, igual que una carga.
    """
    hoy = hoy or timezone.localdate()
    exigibles = [d for d in documentos if d.exigible]
    conteo = Counter(d.semaforo(hoy) for d in exigibles)
    otros = Counter(d.semaforo(hoy) for d in documentos if not d.exigible)
    total = len(exigibles)
    en_plazo = conteo['a_tiempo'] + conteo['por_vencer'] + conteo['sin_plazo']
    return {
        'total': total,
        'validados': conteo['validado'],
        'por_validar': conteo['por_validar'],
        'vencidos': conteo['vencido'],
        'observados': conteo['observado'],
        'no_abiertos': conteo['no_abierto'],
        'pendientes': en_plazo,
        'automaticos': sum(1 for d in exigibles if d.exigido.automatico),
        'evaluados': sum(1 for d in exigibles if d.evaluacion is not None),
        'en_mejora': sum(1 for d in exigibles if d.etapa(hoy) == 'mejora'),
        'no_aplican': otros['no_aplica'],
        'completo': round(100 * conteo['validado'] / total) if total else 100,
        # Lo que la Dirección tiene que mirar hoy: vencido u observado.
        'incumple': conteo['vencido'] + conteo['observado'],
    }


# -- el explorador ---------------------------------------------------------------

NOMBRES_ENTREGA = {
    'PLANIFICACION': ('Planificación', 'Abre el período'),
    'INFORME-SEMESTRAL': ('Informe de cierre', 'Cierra el período'),
}


def _preparar(documento, hoy, cortes, categorias):
    """Lo que la pantalla necesita de cada fila, calculado una sola vez."""
    from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega

    documento.resumen_interfaz = resumen_de_entrega(documento)
    documento.tramo_documental = tramo_del_documento(documento, cortes)
    documento.periodo_legado = documento.marco_periodo == 'academico_legacy'
    documento.periodo_marco_etiqueta = ('Alcance histórico conservado' if documento.periodo_legado
                                       else 'Semestre de gestión' if documento.corte else 'Año de gestión')
    documento.semaforo_actual = documento.semaforo(hoy)
    documento.nombre_semaforo = NOMBRES_SEMAFORO[documento.semaforo_actual]
    documento.etapa_actual = documento.etapa(hoy)
    documento.nombre_etapa = NOMBRES_ETAPA[documento.etapa_actual]
    # El informe del que sale un anexo se abre en el visor, con las fechas de
    # su período, sin salir del expediente. Es la consulta con filtros de la
    # consola, en PDF, para revisarlo o descargarlo ahí mismo.
    # El informe del que sale el anexo: su dirección sin fechas y el rango del
    # período. El visor arma el resto, para consultar otro rango sin salir de aquí.
    documento.url_informe = documento.desde = documento.hasta = ''
    fuente = documento.exigido.fuente_reporte
    if fuente == 'mejora' and documento.pk:
        # Se consolida desde los informes: su vista previa es el mismo PDF que se archiva. Un anexo que todavía
        # no existe en la base se consulta, como antes, en el Centro de reportes.
        inicio, fin = tramo_del_documento(documento, cortes)
        documento.url_informe = reverse('pdf_borrador_documento_expediente', args=[documento.unidad.slug, documento.pk])
        documento.desde, documento.hasta = inicio.isoformat(), fin.isoformat()
    elif fuente in categorias:
        inicio, fin = tramo_del_documento(documento, cortes)
        documento.url_informe = (
            reverse('gestion_reporte_unidad_pdf', args=[documento.unidad.slug])
            + f'?categoria_reporte={fuente}')
        documento.desde, documento.hasta = inicio.isoformat(), fin.isoformat()
    return documento


def consultas_de_la_unidad(unidad, inicio, fin):
    """Los informes que no son evidencia: gestión, en PDF del período, para verlos desde el expediente."""
    from apps.gestion_unidades.presentation.gestion_reportes import categorias_para, documentos_del_expediente

    evidencia = set(documentos_del_expediente(unidad))
    base = reverse('gestion_reporte_unidad_pdf', args=[unidad.slug])
    return [
        {'codigo': codigo, 'nombre': nombre,
         'url': f'{base}?categoria_reporte={codigo}&desde={inicio}&hasta={fin}',
         'base': f'{base}?categoria_reporte={codigo}',
         'desde': inicio.isoformat(), 'hasta': fin.isoformat()}
        for codigo, nombre in categorias_para(unidad)
        if codigo not in evidencia
    ]


@politica_consistente
def arbol_del_expediente(unidad, anio, hoy=None, cortes=None):
    """El expediente como carpetas: lo de la unidad, y por período sus dos documentos con sus anexos.

    Es la lectura que pediste como explorador de archivos: en cada período hay
    dos documentos firmados y, dentro de cada uno, la carpeta «Anexos» con lo
    que el sistema produjo. Nada de lo que hay ahí abajo es una obligación
    aparte; lo que se entrega y se valida son los dos documentos.
    """
    hoy = hoy or timezone.localdate()
    cortes = cortes or cortes_del_anio(anio)
    categorias = _categorias_de_reporte(unidad)
    documentos = leer_expediente(unidad, anio, hoy)
    from apps.documentos.presentation.organizacion_expediente import contextualizar_soportes_planificacion
    contextualizar_soportes_planificacion(documentos)
    redacciones = {
        r.documento_id: r for r in DocumentoElaborado.objects.filter(documento__in=[d.pk for d in documentos])
    }
    for documento in documentos:
        if documento.exigido.codigo == 'PLAN-COMPRAS-ANUAL':
            from apps.documentos.presentation.priorizacion_compras import analizar_priorizacion
            redaccion_compras = redacciones.get(documento.pk)
            documento.priorizacion_inversion = analizar_priorizacion(
                documento, redaccion_compras.contenido if redaccion_compras else {}, hoy=hoy)
        _preparar(documento, hoy, cortes, categorias)
        documento.avance_redaccion = None
        if documento.exigido.redactable:
            redaccion = redacciones.get(documento.pk)
            documento.avance_redaccion = avance(
                documento.exigido.fuente_reporte, redaccion.contenido if redaccion else {})['porcentaje']
    from .progreso_documento import completar_avances
    completar_avances(documentos, redacciones=redacciones)

    de_la_unidad = sorted(
        (d for d in documentos if d.exigido.periodicidad == 'unica' and not d.exigido.es_anexo),
        key=lambda d: (d.exigido.orden, d.exigido.codigo))
    # Lo que se entrega una vez por año y no viaja con ningún período: el plan de compras.
    del_anio = sorted(
        (d for d in documentos if d.exigido.periodicidad == 'anual' and not d.exigido.es_anexo and not d.mes),
        key=lambda d: (d.exigido.orden, d.exigido.codigo))
    periodos = []
    for corte in ('A', 'B'):
        entregas = []
        firmados = sorted(
            (d for d in documentos
             if d.corte == corte and not d.mes and not d.exigido.es_anexo and d.exigido.periodicidad != 'unica'),
            key=lambda d: (0 if d.exigido.plazo_regla == 'inicio' else 1, d.exigido.orden))
        for documento in firmados:
            anexos = [d for d in documentos if d.exigido.anexo_de_id == documento.exigido_id
                      and d.corte == documento.corte and d.mes is None]
            for anexo in anexos:
                if not hasattr(anexo, 'semaforo_actual'):
                    _preparar(anexo, hoy, cortes, categorias)
            nombre, papel = NOMBRES_ENTREGA.get(documento.exigido.codigo, (documento.nombre_documental, ''))
            from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
            if es_unidad_auditable(unidad):
                nombre = documento.nombre_documental
            metas = None
            inicio_documento, fin_documento = tramo_del_documento(documento, cortes)
            if documento.exigido.codigo == 'INFORME-SEMESTRAL' and inicio_documento <= hoy:
                from apps.documentos.presentation.expediente_redaccion import metas_del_periodo
                metas = metas_del_periodo(documento, inicio_documento, fin_documento)
            cierre = None
            if documento.exigido.codigo == 'INFORME-SEMESTRAL':
                from apps.documentos.presentation.evaluacion_cierre import lectura_cierre, detalle_anexo
                cierre = lectura_cierre(documento, metas)
                documento._avance_cierre = cierre
                archivados = {a['documento']: a for a in cierre.get('anexos', [])}
                for anexo in anexos:
                    archivado = archivados.get(anexo.pk, {})
                    anexo.indicadores_cierre = archivado.get('detalle_indicadores') or detalle_anexo(
                        anexo.exigido.codigo, cierre, archivado.get('indicadores'))
                    anexo._avance_archivado = bool(cierre.get('congelado'))
            entregas.append({
                'documento': documento, 'nombre': nombre, 'papel': papel, 'anexos': anexos,
                'anexos_integrados': [a for a in anexos if getattr(a, 'soporte_planificacion', None)],
                'anexos_listos': sum(1 for a in anexos if a.recurso_id),
                'anexos_validados': sum(1 for a in anexos if a.estado == 'validado'),
                'metas': metas,
                'cierre': cierre,
            })
        # El anexo inicial de prácticas representa la misma meta de FT02 que
        # acompaña al cierre. Mostrar su avance evita que quede como tarjeta
        # aislada, sin inventar una obligación o un 100 % por tener un PDF.
        informe = next((e for e in entregas if e['cierre']), None)
        if informe:
            documento_informe = informe['documento']
            for entrega in entregas:
                for anexo in entrega['anexos']:
                    if (anexo.exigido.codigo == 'INDICADORES-PLAN'
                            and tramo_del_documento(anexo, cortes) == tramo_del_documento(documento_informe, cortes)
                            and anexo.marco_periodo == documento_informe.marco_periodo):
                        anexo.indicadores_cierre = detalle_anexo('PRACTICAS-FT02', informe['cierre'])
                        anexo._avance_archivado = bool(informe['cierre'].get('congelado'))
        completar_avances([d for e in entregas for d in [e['documento'], *e['anexos']]], redacciones=redacciones)
        propios = [d for d in del_periodo(documentos, corte, cortes) if d.corte == corte]
        periodos.append({
            'corte': corte, 'etiqueta': f'{anio}-{corte}', 'inicio': cortes[corte][0], 'fin': cortes[corte][1],
            'evaluaciones_previas': evaluaciones_del_periodo_anterior(unidad, anio, corte),
            'vigente': periodo_vigente(cortes, hoy) == corte and anio == hoy.year,
            'cerrado': cortes[corte][1] < hoy,
            'entregas': entregas, 'resumen': resumen(propios, hoy),
        })
    return {
        'documentos': documentos,
        'de_la_unidad': de_la_unidad,
        'requiere_preparacion': any(d.pk is None for d in documentos),
        'del_anio': del_anio,
        'periodos': periodos,
        'resumen_unidad': resumen(de_la_unidad, hoy),
        'resumen_anio': resumen(del_anio, hoy),
        'resumen_anual': resumen(documentos, hoy),
    }


# -- archivo -------------------------------------------------------------------

def carpeta_del_expediente(unidad, anio, carpeta):
    raiz, _ = CarpetaRecurso.objects.get_or_create(
        unidad=unidad, nombre=f'Expediente de calidad {anio}', carpeta_padre=None,
        defaults={'modulo': 'informacionGeneral', 'visibilidad': 'interna', 'activa': True, 'orden': 900,
                  'del_expediente': True},
    )
    # Los nombres son únicos por unidad, incluso entre raíces diferentes.
    # Conserva las carpetas existentes y distingue la hija de otro año sin
    # mover sus archivos ni reutilizar accidentalmente una carpeta ajena.
    base = NOMBRES_CARPETA[carpeta]
    nombre, sufijo = base, 0
    while True:
        hija, _ = CarpetaRecurso.objects.get_or_create(
            unidad=unidad, nombre=nombre,
            defaults={'carpeta_padre': raiz, 'modulo': 'informacionGeneral',
                      'visibilidad': 'interna', 'activa': True,
                      'orden': [c for c, _ in CARPETAS].index(carpeta), 'del_expediente': True},
        )
        if hija.carpeta_padre_id == raiz.pk:
            break
        sufijo += 1
        nombre = f'{base} {anio}' + (f' ({sufijo})' if sufijo > 1 else '')
    # Una carpeta con el mismo nombre creada a mano antes de esta marca pasa al expediente.
    CarpetaRecurso.objects.filter(pk__in=(raiz.pk, hija.pk), del_expediente=False).update(del_expediente=True)
    return hija


def _archivar(documento, contenido, nombre_archivo, autor, descripcion, tipo_adjunto):
    """Guarda el archivo como recurso interno de la unidad y lo apunta desde el expediente."""
    if getattr(documento, '_token_emision', None):
        from .aprobacion_en_linea import sellar_documento
        contenido = sellar_documento(contenido, documento, documento._emisor_emision)
    anterior = documento.recurso
    if anterior is None and documento.version:
        from apps.documentos.presentation.expediente_archivos import versiones_del_documento
        anteriores = versiones_del_documento(documento)
        anterior = anteriores[0]['recurso'] if anteriores else None
    compartido = bool(anterior and anterior.documentos_expediente.exclude(pk=documento.pk).exists())
    recurso = Recurso(
        unidad=documento.unidad,
        carpeta=carpeta_del_expediente(documento.unidad, documento.anio, documento.exigido.carpeta),
        nombre=f'{documento.nombre_documental} · {documento.etiqueta_corte} · v{documento.version + 1}',
        descripcion=descripcion,
        tipo_adjunto=tipo_adjunto,
        visibilidad='interna',
        descargar=True,
        autor=autor[:180],
        fecha_documento=timezone.localdate(),
        version=documento.version + 1,
        reemplaza_a=anterior,
        estado='vigente',
        # Generar un PDF o detectar una firma no equivale a una revisión antivirus.
        seguridad_verificada=False,
        palabras_clave=f'expediente, {documento.exigido.carpeta}, {documento.anio}',
    )
    recurso.archivo.save(nombre_archivo, ContentFile(contenido), save=False)
    recordar_archivo(recurso.archivo)
    try:
        recurso.full_clean()
        recordar_extraccion(recurso)
        recurso.save(conservar_reemplazado=compartido)
    finally:
        recurso.archivo.close()
    if anterior is not None and not compartido:
        # La sustitución de este año no retira la evidencia de otro expediente.
        Recurso.objects.filter(pk=anterior.pk).update(estado='obsoleto')
    documento.recurso = recurso
    documento.version += 1
    _invalidar_evaluacion(documento)
    documento.firma_verificada = False
    documento.verificacion_qr = None
    documento.entregado_en = None
    if not documento.correccion_hasta:
        documento.entregado_tarde = False
    documento.cargado_en = None
    documento.cargado_por = None
    documento.generado_en = None
    documento.recibido_en = None
    documento.recibido_por = None
    documento.validado_en = None
    documento.validado_por = None
    return recurso


def _exigir_entrega_abierta(documento, usuario=None):
    """La entrega está abierta: no se envió todavía y su plazo no venció sin habilitación.

    Un documento validado y enviado no se toca: solo la Dirección lo devuelve
    observado. Y vencido el plazo la entrega no se cierra para siempre —el
    control de calidad necesita el documento igual—, pero deja de ser un
    trámite de la unidad: el responsable lo solicita, la Dirección lo habilita
    y lo que llegue queda marcado como tardío.
    """
    if documento.estado == 'validado':
        raise ValidationError(
            'Este documento ya fue validado y enviado a la Dirección; no se reemplaza. '
            'Si hay que corregirlo, la Dirección lo devuelve observado y se abre una versión nueva.')
    if documento.correccion_hasta:
        if not documento.correccion_abierta and not (usuario is not None and usuario.is_superuser):
            raise ValidationError('El plazo de corrección venció. Solicita una reapertura justificada a Dirección.')
        return
    if not documento.abierto and not (usuario is not None and usuario.is_superuser):
        raise ValidationError(f'La entrega se abre el {documento.abre_el:%d/%m/%Y}.')
    if (documento.vencido and not documento.prorroga_activa
            and not (usuario is not None and usuario.is_superuser)):
        if not documento.ultimatum_hasta:
            raise ValidationError('El plazo institucional venció. La Dirección debe establecer el ultimátum colectivo.')
        raise ValidationError(
            f'El plazo venció el {documento.vence_el:%d/%m/%Y}. Solicita a la Dirección la entrega fuera '
            'de plazo: el documento se recibe igual, queda marcado como tardío y descuenta puntos del '
            'cumplimiento de la unidad.')


def _marcar_tardanza(documento):
    """Deja la marca de entrega tardía en memoria; la persiste el guardado del que entrega."""
    documento.entregado_en = documento.entregado_en or timezone.now()
    if documento.correccion_hasta:
        return  # La corrección autorizada conserva la puntualidad de la entrega inicial.
    documento.entregado_tarde = bool(
        documento.plazo_original and documento.entregado_en > documento.plazo_original)


@comando
def generar_documento(documento, usuario):
    """Produce el documento firmable y, con él, todos sus anexos.

    Un anexo no se genera suelto: sale cuando sale el documento que lo lleva,
    con las fechas de ese período. Así la evidencia es de la misma fecha que
    el informe que la presenta.
    """
    if documento.exigido.es_anexo:
        raise ValidationError(
            f'{documento.nombre_documental} es un anexo: se genera con «{documento.exigido.anexo_de.nombre}».')
    _exigir_entrega_abierta(documento, usuario)
    if documento.exigido.codigo == 'INFORME-SEMESTRAL':
        generar_anexos(documento, usuario)
    _generar(documento, usuario)
    if documento.exigido.codigo == 'INFORME-SEMESTRAL':
        from apps.documentos.presentation.evaluacion_cierre import preparar_cierre
        preparar_cierre(documento, usuario)
    if documento.exigido.codigo != 'INFORME-SEMESTRAL':
        generar_anexos(documento, usuario)


@comando
def _generar(documento, usuario):
    """Produce el PDF desde el Centro de reportes con las fechas del tramo y lo archiva."""
    from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf

    if documento.estado == 'validado':
        raise ValidationError('Un documento enviado no se reemplaza.')

    exigido = documento.exigido
    if not exigido.generable:
        raise ValidationError('Este documento no lo genera el sistema; cárgalo desde la unidad.')
    inicio, fin = tramo_del_documento(documento)
    if exigido.redactable or exigido.fuente_reporte == 'mejora':
        return _generar_redactado(documento, usuario, inicio, fin)
    peticion = HttpRequest()
    peticion.method = 'GET'
    peticion.GET = QueryDict(urlencode({
        'categoria_reporte': exigido.fuente_reporte, 'desde': inicio.isoformat(), 'hasta': fin.isoformat(),
    }))
    peticion.user = usuario
    reporte = build_unit_report(peticion, documento.unidad)
    if reporte['category'] != exigido.fuente_reporte:
        raise ValidationError('La categoría de reporte configurada no está disponible para esta unidad.')
    contenido = render_unit_report_pdf(reporte)
    with transaction.atomic():
        _archivar(
            documento, contenido,
            f'{exigido.codigo}-{documento.anio}{documento.corte}{f"-{documento.mes:02d}" if documento.mes else ""}.pdf',
            autor='Generado por el sistema',
            descripcion=f'{exigido.nombre} del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}, generado desde el Centro de reportes.',
            tipo_adjunto='informe',
        )
        documento.estado = 'generado'
        documento.generado_en = timezone.now()
        if not documento.correccion_hasta:
            documento.observacion = ''
        documento.save()


def _generar_redactado(documento, usuario, inicio, fin):
    """El PDF sale del editor guiado (o del consolidado de mejora) y queda listo para firmar."""
    exigido = documento.exigido
    if exigido.redactable:
        redaccion = obtener_redaccion(documento)
        contenido = pdf_del_documento(documento, redaccion, inicio, fin)
        autor = usuario.get_full_name() or usuario.get_username()
        descripcion = (f'{exigido.nombre} del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}, redactado con el editor guiado; '
                       + ('aprobación en la plataforma y verificación QR.' if getattr(documento, '_token_emision', None)
                          else 'pendiente de firma electrónica.'))
    else:
        redaccion = None
        contenido = pdf_acciones_de_mejora(documento, inicio, fin)
        autor = 'Generado por el sistema'
        descripcion = f'{exigido.nombre} del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}, consolidado desde los informes.'
    with transaction.atomic():
        _archivar(
            documento, contenido, f'{exigido.codigo}-{documento.anio}{documento.corte}.pdf',
            autor=autor, descripcion=descripcion, tipo_adjunto='informe',
        )
        documento.estado = 'generado'
        documento.generado_en = timezone.now()
        if not documento.correccion_hasta:
            documento.observacion = ''
        documento.save()
        if redaccion is not None:
            redaccion.generado_en = documento.generado_en
            redaccion.generado_version = redaccion.version
            redaccion.save()


@comando
def marcar_no_aplica(documento, usuario, justificacion):
    """La unidad declara que ese documento no le corresponde; queda fuera de su cumplimiento."""
    if not documento.exigido.condicional:
        raise ValidationError('Este documento es exigible a todas las unidades; no admite «no aplica».')
    if documento.estado in ('cargado', 'validado', 'generado') and documento.recurso_id:
        raise ValidationError('El documento ya tiene un archivo; no se puede marcar como no aplicable.')
    if not (justificacion or '').strip():
        raise ValidationError('Escribe por qué no aplica: la justificación queda en el expediente.')
    documento.estado = 'no_aplica'
    documento.observacion = justificacion.strip()
    documento.cargado_en = timezone.now()
    documento.cargado_por = usuario
    documento.save(update_fields=['estado', 'observacion', 'cargado_en', 'cargado_por', 'actualizado_en'])


@comando
def reactivar_documento(documento, usuario):
    if documento.estado != 'no_aplica':
        raise ValidationError('Solo se reactiva un documento marcado como no aplicable.')
    documento.estado = 'pendiente'
    documento.observacion = ''
    documento.save(update_fields=['estado', 'observacion', 'actualizado_en'])


@comando
def cargar_documento(documento, archivo, usuario, descripcion='', *, declaracion_correspondencia=None):
    """Recibe el archivo de la unidad; si el documento exige firma, el PDF debe traerla."""
    exigido = documento.exigido
    if not exigido.cargable:
        raise ValidationError('Este documento lo genera el sistema; no admite cargas.')
    _exigir_entrega_abierta(documento, usuario)
    if archivo is None:
        raise ValidationError('Adjunta el archivo del documento.')
    if exigido.requiere_firma:
        try:
            detalle = validar_pdf_firmado(archivo)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        firmas = f"{detalle['firmas']} firma(s) electrónica(s) detectada(s) · SHA-256 {detalle['sha256'][:16]}"
    else:
        if Path(archivo.name).suffix.lower() not in FORMATOS_ADJUNTO_PERMITIDOS:
            raise ValidationError(f'El archivo {archivo.name} no tiene un formato admitido.')
        if archivo.size > MAXIMO_BYTES_CARGA:
            raise ValidationError('El archivo supera el máximo de 25 MB.')
        firmas = ''
    from apps.documentos.presentation.expediente_archivos import comprobar_correspondencia, registrar_integridad_documental
    from apps.documentos.presentation.expediente_operaciones import declaracion_actual
    integridad = comprobar_correspondencia(documento, archivo,
        declaracion=declaracion_actual(documento, declaracion_correspondencia))
    descripcion = (descripcion or '').strip() or f'{exigido.nombre} cargado por la unidad.'
    if firmas:
        descripcion = f'{descripcion} {firmas}'
    archivo.seek(0)
    with transaction.atomic():
        _archivar(
            documento, archivo.read(), archivo.name, autor=usuario.get_full_name() or usuario.get_username(),
            descripcion=descripcion, tipo_adjunto='certificado' if exigido.requiere_firma else 'informe',
        )
        documento.estado = 'cargado'
        documento.firma_verificada = exigido.requiere_firma
        _marcar_tardanza(documento)
        documento.cargado_en = timezone.now()
        documento.cargado_por = usuario
        if not documento.correccion_hasta:
            documento.observacion = ''
        documento.save()
        registrar_integridad_documental(documento, usuario, integridad, etapa='cargar')
    # Cargar la firma no recalcula las evidencias que acompañaron al original.
    # Las actualizaciones explícitas del informe generan una nueva versión.
    generar_anexos(documento, usuario, solo_faltantes=True)


@comando
def validar_documento(documento, usuario, *, declaracion_correspondencia=None):
    """Alguien da por buena la entrega; sin eso, archivarla no cierra nada.

    Quien administra la unidad puede validar lo que ella misma produjo: la
    Dirección revisa después el consolidado y puede observarlo. Lo que no se
    admite es validar aire: tiene que existir el archivo.
    """
    _exigir_cierre_concluido(documento)
    if documento.exigido.es_anexo:
        raise ValidationError(
            f'{documento.nombre_documental} es un anexo: se valida con «{documento.exigido.anexo_de.nombre}».')
    if documento.estado not in ('cargado', 'generado', 'observado'):
        raise ValidationError('Solo se valida un documento generado o cargado.')
    if not documento.recurso_id:
        raise ValidationError('Primero genera o carga el documento: no hay nada que validar.')
    if documento.entregado_en is None or documento.correccion_hasta:
        _exigir_entrega_abierta(documento, usuario)
    if documento.firma_pendiente:
        raise ValidationError(
            'Este documento se entrega firmado: carga el PDF con la firma electrónica antes de validarlo.')
    from apps.documentos.presentation.expediente_archivos import exigir_integridad_documental
    from apps.documentos.presentation.expediente_operaciones import declaracion_actual
    emision = None
    if documento.verificacion_qr:
        from .aprobacion_en_linea import comprobar_emision, declaracion_nativa
        emision = comprobar_emision(documento)
        if emision.observado_en:
            raise ValidationError('Prepara una nueva versión para atender la observación de Dirección.')
        declaracion_correspondencia = declaracion_nativa(documento)
    from .preparacion_documental import exigir_editor_archivado, exigir_condiciones_cierre
    if exigir_editor_archivado(documento):
        exigir_condiciones_cierre(documento)
    exigir_integridad_documental(documento, usuario, etapa='enviar',
        declaracion=declaracion_actual(documento, declaracion_correspondencia, etapa='enviar'))
    if documento.exigido.codigo != 'INFORME-SEMESTRAL':
        from apps.documentos.presentation.automatizacion_documental import procesar_expediente
        procesar_expediente(anexos_del(documento), usuario=usuario)
    pendientes = anexos_sin_revisar(documento) if documento.exigido.codigo != 'INFORME-SEMESTRAL' else []
    if pendientes and not documento.verificacion_qr:
        nombres = '; '.join(a.nombre_documental for a in pendientes[:3])
        raise ValidationError(
            f'Faltan por revisar y validar {len(pendientes)} anexo(s) ({nombres}{"…" if len(pendientes) > 3 else ""}). '
            'Ábrelos, comprueba que la información sea correcta y valídalos antes de enviar.')
    with transaction.atomic():
        if documento.exigido.codigo == 'INFORME-SEMESTRAL':
            from apps.documentos.presentation.evaluacion_cierre import calcular_cierre, congelar_cierre
            if calcular_cierre(documento).get('demostracion'):
                raise ValidationError('El período contiene evidencias de demostración; no se envía como entrega oficial.')
            congelar_cierre(documento, usuario)
        documento.estado = 'validado'
        _marcar_tardanza(documento)
        documento.validado_en = timezone.now()
        documento.validado_por = usuario
        documento.save(update_fields=['estado', 'validado_en', 'validado_por', 'entregado_en',
                                      'entregado_tarde', 'actualizado_en'])
        cerrar_anexos(documento, usuario)
        if emision:
            emision.enviado_por, emision.enviado_en = usuario, timezone.now()
            emision.save(update_fields=['enviado_por', 'enviado_en'])
            documento._constancia_qr = emision
        from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
        if es_unidad_auditable(documento.unidad):
            from apps.documentos.presentation.automatizacion_documental import procesar_documento
            procesar_documento(documento, usuario=usuario)


def _invalidar_evaluacion(documento):
    documento.evaluacion = None
    documento.evaluacion_version = None
    documento.evaluado_en = None
    documento.evaluado_por = None
    for campo in ('observacion', 'fortalezas', 'debilidades', 'recomendaciones'):
        setattr(documento, f'evaluacion_{campo}', '')


@comando
def anotar_observacion(documento, usuario, observacion, *, version, recurso_id, huella,
                      huella_anterior, motivo):
    """Prepara el motivo de una acción administrativa sin sobrescribir el estado."""
    if not usuario.is_active or not usuario.is_superuser:
        raise ValidationError('Solo la Dirección anota observaciones desde la administración.')
    from .observaciones_documentales import _guardar_texto
    _guardar_texto(documento, usuario, 'observacion', observacion, version=version,
        recurso_id=recurso_id, huella=huella, huella_anterior=huella_anterior, motivo=motivo)


@comando
def observar_documento(documento, usuario, observacion, hasta=None):
    """Devuelve el documento con motivo y fecha futura de corrección.

    Lo que ya está enviado solo lo devuelve la Dirección: es la única forma
    de reabrir un documento validado, y deja constancia de quién y por qué.
    """
    if documento.exigido.es_anexo:
        raise ValidationError(
            f'{documento.nombre_documental} es un anexo: se observa «{documento.exigido.anexo_de.nombre}».')
    if not usuario.is_active or not usuario.is_superuser:
        raise ValidationError('Solo la Dirección devuelve documentos para corregir.')
    if not (observacion or '').strip():
        raise ValidationError('Escribe el motivo de la observación: la unidad lo necesita para corregir.')
    if isinstance(hasta, str):
        from django.utils.dateparse import parse_datetime
        try:
            hasta = parse_datetime(hasta)
        except ValueError:
            hasta = None
    if hasta is None:
        raise ValidationError('Indica la fecha y hora límite para corregir y reenviar.')
    if timezone.is_naive(hasta):
        hasta = timezone.make_aware(hasta)
    if hasta <= timezone.now():
        raise ValidationError('La fecha de corrección debe ser futura.')
    with transaction.atomic():
        from apps.documentos.presentation.conformidad_permanente import revocar_permanente
        revocar_permanente(documento, usuario, observacion)
        documento.estado = 'observado'
        documento.observacion = observacion.strip()
        documento.correccion_hasta = hasta
        documento.prorroga_hasta = None  # La nueva devolución establece su propio cierre.
        documento.tardanza_pedida_en = None  # Una apertura futura requiere una solicitud nueva.
        documento.validado_en = timezone.now()
        documento.validado_por = usuario
        # Devuelto, la recepción anterior ya no vale: lo que vuelva se recibe de nuevo.
        documento.recibido_en = None
        documento.recibido_por = None
        _invalidar_evaluacion(documento)
        documento.save()
        reabrir_anexos(documento)


@comando
def recibir_documento(documento, usuario, *, declaracion_correspondencia=None):
    """La Dirección da por recibida una entrega archivada que la unidad no validó.

    Lo que cuenta en un control de calidad es contar con el documento, no la
    ceremonia: si el responsable lo subió y no alcanzó a validarlo, el director
    del sistema lo recibe y lo califica. Queda quién lo recibió, cuándo, y si
    llegó fuera de plazo, porque eso le descuenta puntos a la unidad.
    """
    _exigir_cierre_concluido(documento)
    if documento.exigido.es_anexo:
        raise ValidationError(
            f'{documento.nombre_documental} es un anexo: se recibe «{documento.exigido.anexo_de.nombre}».')
    if not usuario.is_superuser:
        raise ValidationError('Solo la Dirección da por recibida una entrega que la unidad no validó.')
    if not documento.recurso_id:
        raise ValidationError('No hay documento archivado: no se recibe lo que todavía no existe.')
    if documento.firma_pendiente:
        raise ValidationError('Carga el PDF firmado antes de recibir esta entrega.')
    if documento.verificacion_qr:
        from .aprobacion_en_linea import comprobar_emision
        constancia = comprobar_emision(documento)
        if documento.estado != 'validado' or not constancia.enviado_en:
            raise ValidationError('La unidad debe enviar esta versión antes de que Dirección pueda recibirla.')
    from .preparacion_documental import exigir_editor_archivado, exigir_condiciones_cierre
    if exigir_editor_archivado(documento):
        exigir_condiciones_cierre(documento)
    from apps.documentos.presentation.expediente_archivos import exigir_integridad_documental
    from apps.documentos.presentation.expediente_operaciones import declaracion_actual
    exigir_integridad_documental(documento, usuario, etapa='recibir',
        declaracion=declaracion_actual(documento, declaracion_correspondencia))
    if documento.recibido_en is not None and documento.estado == 'validado':
        return
    with transaction.atomic():
        if documento.exigido.codigo == 'INFORME-SEMESTRAL' and documento.estado != 'validado':
            from apps.documentos.presentation.evaluacion_cierre import congelar_cierre
            congelar_cierre(documento, usuario)
        documento.estado = 'validado'
        documento.validado_en = documento.validado_en or timezone.now()
        documento.validado_por = documento.validado_por or usuario
        documento.recibido_en = timezone.now()
        documento.recibido_por = usuario
        documento.observacion = ''
        _marcar_tardanza(documento)
        documento.save(update_fields=['estado', 'validado_en', 'validado_por', 'recibido_en', 'recibido_por',
                                      'entregado_en', 'entregado_tarde', 'observacion', 'actualizado_en'])
        cerrar_anexos(documento, usuario)


@comando
def solicitar_entrega_tardia(documento, usuario, motivo):
    """El responsable de la unidad pide entregar vencido el plazo, y dice por qué.

    Sin esta solicitud la Dirección no habilita nada: la excepción se pide, se
    justifica y queda escrita en el expediente.
    """
    if documento.estado == 'validado':
        raise ValidationError('Este documento ya fue enviado.')
    if not documento.correccion_hasta and (not documento.ultimatum_hasta or documento.ultimatum_activo):
        raise ValidationError('Primero corresponde el ultimátum colectivo de la Dirección. La solicitud individual procede después de su vencimiento.')
    if documento.correccion_hasta and documento.correccion_abierta:
        raise ValidationError('La corrección todavía está abierta.')
    if not documento.vencido and not documento.correccion_hasta:
        raise ValidationError('El plazo no ha vencido: la entrega está abierta.')
    if documento.prorroga_activa and not documento.correccion_hasta:
        raise ValidationError('Ya tienes una reapertura vigente para esta entrega.')
    motivo = (motivo or '').strip()
    if not motivo:
        raise ValidationError('Escribe por qué no se entregó dentro del plazo: la Dirección decide con eso.')
    documento.tardanza_motivo = motivo
    documento.tardanza_pedida_en = timezone.now()
    documento.save(update_fields=['tardanza_motivo', 'tardanza_pedida_en', 'actualizado_en'])


@comando
def habilitar_entrega_tardia(documento, usuario, hasta=None):
    """La Dirección abre la entrega vencida que la unidad solicitó."""
    if not usuario.is_superuser:
        raise ValidationError('Solo la Dirección habilita una entrega fuera de plazo.')
    if not documento.correccion_hasta and (not documento.ultimatum_hasta or documento.ultimatum_activo):
        raise ValidationError('La reapertura individual procede después del ultimátum colectivo vencido.')
    if documento.estado == 'validado':
        raise ValidationError('Este documento ya fue enviado: no hay nada que habilitar.')
    if documento.tardanza_pedida_en is None:
        raise ValidationError(
            'La habilitación responde a una solicitud: el responsable de la unidad tiene que pedirla primero.')
    if documento.correccion_hasta and documento.correccion_abierta:
        raise ValidationError('La corrección todavía está abierta.')
    if not documento.vencido and not documento.correccion_hasta:
        raise ValidationError('Solo se reabre una entrega cuyo plazo original venció.')
    if documento.prorroga_activa and not documento.correccion_hasta:
        raise ValidationError('La unidad ya tiene una reapertura vigente.')
    if (documento.tardanza_habilitada_en and
            documento.tardanza_pedida_en <= documento.tardanza_habilitada_en):
        raise ValidationError('La unidad debe justificar una nueva solicitud de reapertura.')
    if hasta is None:
        raise ValidationError('Indica la fecha y hora de cierre de la reapertura.')
    if isinstance(hasta, str):
        from django.utils.dateparse import parse_datetime
        try:
            hasta = parse_datetime(hasta)
        except ValueError:
            hasta = None
        if hasta is None:
            raise ValidationError('Indica una fecha y hora de cierre válidas.')
    if timezone.is_naive(hasta):
        hasta = timezone.make_aware(hasta)
    if hasta <= timezone.now():
        raise ValidationError('El cierre debe ser posterior a la fecha y hora actuales.')
    documento.prorroga_hasta = hasta
    documento.tardanza_habilitada_en = timezone.now()
    documento.tardanza_habilitada_por = usuario
    documento.save(update_fields=['tardanza_habilitada_en', 'tardanza_habilitada_por', 'prorroga_hasta', 'actualizado_en'])


@comando
def evaluar_documento(documento, usuario, porcentaje, observacion='', fortalezas='', debilidades='',
                      recomendaciones='', registrar_incumplimiento=False, *, declaracion_correspondencia=None,
                      _registro_conformidad=None, _registro_cierre=None):
    """Registra la nota del informe semestral: la que sale del cumplimiento de sus metas.

    Solo el informe se califica, y solo con su cierre calculado (o con 0 si no se entregó). Los demás documentos
    son de cumplimiento obligatorio y no reciben porcentaje. Bajo el mínimo, el informe pasa a mejora continua y
    las recomendaciones son obligatorias: son lo que la siguiente planificación tiene que responder.
    """
    _exigir_cierre_concluido(documento)
    from apps.documentos.presentation.conformidad_permanente import es_permanente
    if es_permanente(documento):
        raise ValidationError('Este documento permanente se aprueba una sola vez por versión; no se califica con porcentajes.')
    if documento.exigido.es_anexo:
        raise ValidationError(
            f'{documento.nombre_documental} es un anexo: se evalúa «{documento.exigido.anexo_de.nombre}».')
    if not es_calificable(documento.exigido):
        if _registro_conformidad is _REGISTRO_CONFORMIDAD_PLAN:
            return  # La conformidad de un plan queda en su registro de auditoría; un plan no lleva nota.
        raise ValidationError(
            f'{documento.nombre_documental} es de cumplimiento obligatorio: la Dirección lo acepta u observa, '
            'sin porcentaje. Solo el informe semestral se califica, con el cumplimiento de sus metas.')
    if not usuario.is_superuser:
        raise ValidationError('Solo la Dirección evalúa los documentos enviados.')
    if documento.estado != 'validado' and not registrar_incumplimiento:
        raise ValidationError(
            'Se evalúa lo que ya está en manos de la Dirección: la unidad lo valida, o el director lo '
            'da por recibido desde su tablero.')
    try:
        porcentaje = int(porcentaje)
    except (TypeError, ValueError):
        raise ValidationError('El cumplimiento se escribe como un porcentaje de 0 a 100.')
    if not 0 <= porcentaje <= 100:
        raise ValidationError('El cumplimiento se escribe como un porcentaje de 0 a 100.')
    if registrar_incumplimiento and porcentaje != 0:
        raise ValidationError('Una entrega incompleta solo admite 0 por incumplimiento.')
    if not registrar_incumplimiento and _registro_cierre is not _REGISTRO_CIERRE:
        raise ValidationError(
            'La nota del informe semestral sale del cumplimiento de las metas de su planificación, medido con los '
            'registros del período: la Dirección confirma el cierre calculado; no se escribe a mano.')
    if not registrar_incumplimiento:
        from apps.documentos.presentation.expediente_archivos import exigir_integridad_documental
        from apps.documentos.presentation.expediente_operaciones import declaracion_actual
        exigir_integridad_documental(documento, usuario, etapa='evaluar',
            declaracion=declaracion_actual(documento, declaracion_correspondencia))
    observacion = (observacion or '').strip()
    fortalezas, debilidades = (fortalezas or '').strip(), (debilidades or '').strip()
    recomendaciones = (recomendaciones or '').strip()
    minimo = minimo_vigente()
    from apps.documentos.models.expediente import penalizacion_vigente
    nota = max(0, porcentaje - (penalizacion_vigente() if documento.entregado_tarde else 0))
    if nota < minimo and not (observacion or debilidades):
        raise ValidationError(
            f'Por debajo del {minimo} % hay que decir qué falta: es el hallazgo de la mejora continua.')
    if nota < minimo and not recomendaciones:
        raise ValidationError(
            'Por debajo del mínimo hay que recomendar qué atender el siguiente período: '
            'la próxima planificación de la unidad lo tiene que responder.')
    documento.evaluacion = porcentaje
    documento.evaluacion_version = documento.version
    documento.evaluacion_observacion = observacion
    documento.evaluacion_fortalezas = fortalezas
    documento.evaluacion_debilidades = debilidades
    documento.evaluacion_recomendaciones = recomendaciones
    documento.evaluado_en = timezone.now()
    documento.evaluado_por = usuario
    documento.save(update_fields=['evaluacion', 'evaluacion_version', 'evaluacion_observacion', 'evaluacion_fortalezas',
                                  'evaluacion_debilidades', 'evaluacion_recomendaciones', 'evaluado_en',
                                  'evaluado_por', 'actualizado_en'])


def periodo_anterior(anio, corte):
    """(año, corte) del período que antecede al pedido; el año entero antecede a su A."""
    if corte == 'B':
        return anio, 'A'
    return anio - 1, 'B'


def evaluaciones_del_periodo_anterior(unidad, anio, corte):
    """Lo que la Dirección evaluó en el período anterior: la siguiente planificación lo responde."""
    anio_previo, corte_previo = periodo_anterior(anio, corte or 'A')
    return list(
        DocumentoExpediente.objects.filter(
            unidad=unidad, anio=anio_previo, corte=corte_previo, evaluacion__isnull=False, estado='validado',
            exigido__anexo_de__isnull=True,
        ).select_related('exigido', 'evaluado_por').order_by('exigido__orden')
    )


# -- consolidado ---------------------------------------------------------------

def historico_de_periodos(unidad, hoy=None, excluir=None, limite=8):
    """Lo entregado período a período, del más reciente al más antiguo.

    Lee lo que ya está registrado en vez de materializar cada año: el histórico
    cuenta lo que pasó, no lo que habría que exigir hoy hacia atrás.
    """
    hoy = hoy or timezone.localdate()
    documentos = list(
        DocumentoExpediente.objects.filter(unidad=unidad).select_related('exigido'))
    filas = []
    for anio in sorted({d.anio for d in documentos}, reverse=True):
        cortes = cortes_del_anio(anio)
        del_anio = [d for d in documentos if d.anio == anio]
        for corte in ('B', 'A'):
            if excluir == (anio, corte):
                continue
            propios = [d for d in del_periodo(del_anio, corte, cortes) if d.corte == corte]
            if not propios:
                continue
            filas.append({
                'anio': anio, 'corte': corte, 'etiqueta': f'{anio}-{corte}',
                'inicio': cortes[corte][0], 'fin': cortes[corte][1],
                'cerrado': cortes[corte][1] < hoy,
                **resumen(propios, hoy),
            })
    return filas[:limite]


def resumen_unidad(unidad, anio, hoy=None):
    """La fila de una unidad en el tablero por tipo: sus dos firmas por período y lo de una vez."""
    hoy = hoy or timezone.localdate()
    arbol = arbol_del_expediente(unidad, anio, hoy)
    fila = {'unidad': unidad, **arbol['resumen_anual']}
    fila['periodos'] = [
        {'corte': p['corte'], 'entregas': p['entregas'], 'resumen': p['resumen']} for p in arbol['periodos']]
    fila['de_la_unidad'] = arbol['de_la_unidad'] + arbol['del_anio']
    fila['url'] = reverse('gestion_expediente_unidad', args=[unidad.slug]) + f'?anio={anio}'
    return fila


def periodo_pedido(request, hoy=None):
    """(año, corte, cortes) pedidos; por omisión, el año en curso en su período vigente."""
    hoy = hoy or timezone.localdate()
    from apps.gestion_unidades.presentation.reportes_filtros import anio_pedido

    anio = anio_pedido(request.GET.get('anio') or request.POST.get('anio'), hoy.year)
    cortes = cortes_del_anio(anio)
    corte = request.GET.get('corte', request.POST.get('corte'))
    if corte is None:
        # El año en curso abre en su período vigente; un año pasado se lee entero.
        corte = periodo_vigente(cortes, hoy) if anio == hoy.year else ''
    if corte not in ('A', 'B'):
        corte = ''
    return anio, corte, cortes


def nivel_de_cumplimiento(unidad, anio, corte, hoy):
    """Cuánto cumple la unidad en el período, con el informe de mejora si ya se produjo."""
    from apps.documentos.presentation.mejora_continua import cumplimiento_del_periodo, informe_archivado

    datos = cumplimiento_del_periodo(unidad, anio, corte, hoy)
    datos['informe'] = informe_archivado(unidad, anio, corte)
    return datos


def contexto_del_expediente(unidad, anio, corte, cortes, hoy, usuario=None, **extra):
    """Lo que necesita el cuerpo del expediente, venga de su página o de la consola.

    El Centro de reportes abre esta misma pantalla en vez de una copia: si el
    contexto se armara dos veces, las dos lecturas terminarían discrepando.
    """
    from apps.documentos.presentation.mejora_seguimiento import contexto_mejora
    from apps.documentos.presentation.automatizacion_documental import resumen_automatizacion
    from apps.documentos.presentation.escenario_ideal_consulta import escenario_disponible
    from apps.documentos.presentation.guia_reportes import construir_guia_reportes

    arbol = arbol_del_expediente(unidad, anio, hoy, cortes)
    anios = sorted({anio, hoy.year} | set(
        DocumentoExpediente.objects.filter(unidad=unidad).values_list('anio', flat=True)), reverse=True)
    periodos = [p for p in arbol['periodos'] if not corte or p['corte'] == corte]
    entregas_visibles = arbol['de_la_unidad'] + arbol['del_anio'] + [
        entrega['documento'] for periodo in periodos for entrega in periodo['entregas']]
    for numero, documento in enumerate(entregas_visibles, start=1):
        documento.numero_item = numero
    from apps.documentos.presentation.progreso_general import progreso_general
    progreso = progreso_general(entregas_visibles)
    for fila in progreso['detalle']:
        fila['documento'].aporte_cumplimiento = {k: v for k, v in fila.items() if k != 'documento'}
    cumplimiento = nivel_de_cumplimiento(unidad, anio, corte, hoy)
    seguimiento = contexto_mejora(unidad, anio, corte, usuario) if usuario else {}
    tramite = seguimiento.get('tramite_mejora')
    seguimiento['mejora_antecedente'] = bool(
        tramite and not tramite.remitido_en and not cumplimiento['requiere_mejora'])
    return {
        'unidad': unidad,
        'anio': anio,
        'anios': anios,
        'corte': corte,
        'cortes': cortes,
        'etiqueta_periodo': f'Período {anio}-{corte}' if corte else f'Año {anio}',
        'rango_periodo': cortes[corte] if corte else rango_anual(cortes),
        'historico': historico_de_periodos(unidad, hoy, excluir=(anio, corte) if corte else None),
        'de_la_unidad': arbol['de_la_unidad'],
        'requiere_preparacion': arbol['requiere_preparacion'],
        'del_anio': arbol['del_anio'],
        'periodos': periodos,
        'total_entregas': len(entregas_visibles),
        'guia_reportes': construir_guia_reportes(unidad, anio, corte,
            *(cortes[corte] if corte else rango_anual(cortes)), arbol['documentos'], entregas_visibles, usuario),
        'progreso_general': progreso,
        'automatizacion_resumen': resumen_automatizacion(del_periodo(arbol['documentos'], corte, cortes)),
        'escenario_ideal_disponible': escenario_disponible(unidad, anio, corte),
        'resumen_unidad': arbol['resumen_unidad'],
        'resumen_anio': arbol['resumen_anio'],
        'consultas': consultas_de_la_unidad(unidad, *(cortes[corte] if corte else rango_anual(cortes))),
        'cumplimiento': cumplimiento,
        'minimo_cumplimiento': minimo_vigente(),
        'resumen': (periodos[0]['resumen'] if corte and periodos else arbol['resumen_anual']),
        'resumen_anual': arbol['resumen_anual'],
        'hoy': hoy,
        **seguimiento,
        **extra,
    }


# -- vista de la consola -------------------------------------------------------

@login_required
@require_http_methods(['GET', 'POST'])
def expediente_unidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    opera = puede_operar_modulo_unidad(request.user, unidad, 'reportes')
    recibe = es_receptor_de(request.user, unidad)
    if not (opera or recibe):
        raise PermissionDenied('No tienes autorización para el expediente de esta unidad.')
    hoy = timezone.localdate()
    anio, corte, cortes = periodo_pedido(request, hoy)
    destino = reverse('gestion_expediente_unidad', args=[slug]) + f'?anio={anio}&corte={corte}'
    # Abierto desde la consola, la acción devuelve a la consola y no a la
    # página propia: quien entra por el Centro de reportes se queda ahí.
    volver = request.POST.get('volver') or ''
    if volver and url_has_allowed_host_and_scheme(volver, allowed_hosts=None):
        destino = volver

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion in ('evaluar', 'evaluar_rubrica', 'aprobar_permanente', 'confirmar_conformidad', 'recibir', 'habilitar_tardia',
                      'asignar_plazo', 'ultimatum'):
            raise PermissionDenied('Las decisiones de Dirección se realizan en el administrador.')
        if accion in ('remitir_mejora', 'recibir_mejora', 'decidir_mejora',
                      'crear_accion_mejora', 'seguir_mejora'):
            from apps.documentos.presentation.mejora_seguimiento import tramitar_mejora

            try:
                tramitar_mejora(unidad, request.POST.get('informe'), request.user,
                               accion, request.POST, request=request)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                messages.success(request, 'Trámite de mejora registrado.')
            return redirect(destino)
        if not opera:
            raise PermissionDenied(
                'Quien recibe el informe de la dependencia lo lee; las entregas las valida la unidad '
                'y las califica la Dirección.')
        if accion == 'automatizar':
            from apps.documentos.presentation.automatizacion_documental import procesar_expediente
            from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
            if not es_unidad_auditable(unidad):
                raise PermissionDenied('Este tipo de unidad no tiene un perfil de control automático configurado.')
            documentos = preparar_expediente(unidad, anio, request.user, request=request)
            controles = procesar_expediente(del_periodo(documentos, corte, cortes), usuario=request.user)
            aprobados = sum(bool(c and c.aplicado) for c in controles)
            messages.success(request, f'Comprobados {len(controles)} documentos; {aprobados} con validación automática. Los demás muestran qué atender.')
            return redirect(destino)
        if accion == 'preparar':
            preparar_expediente(unidad, anio, request.user, request=request)
            messages.success(request, f'Expediente de {anio} preparado para trabajar.')
            return redirect(destino)
        if accion == 'mejora':
            from apps.documentos.presentation.mejora_continua import generar_informe_de_mejora

            try:
                recurso = generar_informe_de_mejora(unidad, anio, corte, request.user, hoy, request=request)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                messages.success(request, f'Informe de mejora continua archivado (v{recurso.version}).')
            return redirect(destino)
        documento = get_object_or_404(DocumentoExpediente, pk=id_solicitado(request.POST.get('documento')), unidad=unidad)
        ancla = 'anexos' if accion == 'anexos' else 'entrega'
        destino = destino.split('#', 1)[0] + f'#{ancla}-{documento.pk}'
        if accion in ('corregir_observacion', 'corregir_justificacion_tardia'):
            from .observaciones_documentales import corregir_justificacion_tardia
            if accion == 'corregir_observacion' and not request.user.is_superuser:
                raise PermissionDenied('Solo Dirección corrige su observación; la unidad puede aclarar su justificación de tardanza.')
            funcion = anotar_observacion if accion == 'corregir_observacion' else corregir_justificacion_tardia
            try:
                funcion(documento, request.user, request.POST.get('texto', ''),
                    version=request.POST.get('version'), recurso_id=request.POST.get('recurso_id'),
                    huella=request.POST.get('huella'), huella_anterior=request.POST.get('huella_texto'),
                    motivo=request.POST.get('motivo'), request=request)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                messages.success(request, 'Texto corregido. El historial, resultado, plazos y aprobaciones se conservan.')
            return redirect(destino)
        from apps.documentos.presentation.expediente_operaciones import edicion_desde_unidad
        try:
            with edicion_desde_unidad(documento, request.user,
                                     rectificar_anexo=accion in ('rectificar_anexo', 'actualizar_anexo')):
                if accion == 'solicitar_tardia':
                    solicitar_entrega_tardia(documento, request.user, request.POST.get('motivo', ''), request=request)
                    mensaje = (f'Solicitud enviada: la Dirección decide si habilita la entrega de '
                               f'{documento.nombre_documental} ({documento.etiqueta_corte}) fuera de plazo.')
                elif accion == 'generar':
                    generar_documento(documento, request.user, request=request)
                    mensaje = f'{documento.nombre_documental} ({documento.etiqueta_corte}) generado y archivado.'
                elif accion == 'cargar':
                    cargar_documento(documento, request.FILES.get('archivo'), request.user,
                                     request.POST.get('descripcion', ''), request=request)
                    if request.POST.get('enviar') == '1':
                        validar_documento(documento, request.user, request=request)
                        mensaje = f'{documento.nombre_documental} ({documento.etiqueta_corte}) cargado y enviado a la Dirección.'
                    else:
                        mensaje = f'{documento.nombre_documental} ({documento.etiqueta_corte}) cargado; queda por validar.'
                elif accion == 'no_aplica':
                    marcar_no_aplica(documento, request.user, request.POST.get('justificacion', ''), request=request)
                    mensaje = f'{documento.nombre_documental} ({documento.etiqueta_corte}) marcado como no aplicable.'
                elif accion == 'validar':
                    validar_documento(documento, request.user, request=request)
                    mensaje = f'{documento.nombre_documental} ({documento.etiqueta_corte}) enviado a la Dirección.'
                elif accion == 'observar':
                    observar_documento(documento, request.user, request.POST.get('observacion', ''),
                                       hasta=request.POST.get('hasta_correccion'), request=request)
                    mensaje = f'{documento.nombre_documental} ({documento.etiqueta_corte}) observado; la unidad debe corregirlo.'
                elif accion == 'reactivar':
                    reactivar_documento(documento, request.user, request=request)
                    mensaje = f'{documento.nombre_documental} ({documento.etiqueta_corte}) vuelve a exigirse a la unidad.'
                elif accion == 'validar_anexo':
                    validar_anexo(documento, request.user, request=request)
                    mensaje = f'Anexo «{documento.nombre_documental}» ({documento.etiqueta_corte}) revisado y validado.'
                elif accion in ('rectificar_anexo', 'actualizar_anexo'):
                    rectificar_anexo(documento, request.user, request.POST.get('version'),
                                     actualizar=accion == 'actualizar_anexo', request=request)
                    mensaje = ('Anexo actualizado en una nueva versión; revísalo antes de enviar.'
                               if accion == 'actualizar_anexo' else
                               'Revisión retirada. Corrige los registros de origen y actualiza el anexo antes de enviarlo.')
                elif accion == 'anexos':
                    generar_anexos(documento, request.user, request=request)
                    mensaje = f'Anexos de {documento.nombre_documental} ({documento.etiqueta_corte}) actualizados con lo registrado.'
                elif accion == 'retirar_archivo':
                    from apps.documentos.presentation.expediente_archivos import retirar_archivo
                    if request.POST.get('confirmar_retiro') != '1':
                        raise ValidationError('Confirma la retirada del archivo indicado.')
                    retirar_archivo(documento, request.user, request.POST.get('motivo'),
                                    request.POST.get('version'), request.POST.get('huella'), request=request)
                    mensaje = 'Archivo retirado de la entrega; permanece en el historial. Carga el documento correcto.'
                else:
                    raise ValidationError('Acción no reconocida.')
        except ValidationError as error:
            detalle = ' '.join(error.messages)
            if accion == 'cargar' and request.POST.get('enviar') == '1':
                detalle = 'No se cargó ni envió el documento. ' + detalle
            messages.error(request, detalle)
        else:
            messages.success(request, mensaje)
        return redirect(destino)

    contexto = contexto_del_expediente(unidad, anio, corte, cortes, hoy,
                                      usuario=request.user, solo_lectura=not opera)
    seleccion = request.GET.get('gestionar', '')
    if seleccion:
        candidatos = [{'documento': d, 'nombre': d.nombre_documental}
                      for d in contexto['de_la_unidad'] + contexto['del_anio']]
        candidatos += [{**e, 'evaluaciones_previas': p['evaluaciones_previas']}
                       for p in contexto['periodos'] for e in p['entregas']]
        elegida = next((e for e in candidatos if (e['documento'].pk is not None and str(e['documento'].pk) == seleccion)
                       or (e['documento'].pk is None and e['documento'].exigido.codigo == seleccion)), None)
        if elegida is None:
            raise Http404('Documento fuera del expediente seleccionado.')
        seleccionado = elegida['documento']
        anexo_id = request.GET.get('anexo')
        if anexo_id:
            seleccionado = next((a for a in elegida.get('anexos', []) if
                                 (a.pk is not None and str(a.pk) == anexo_id) or
                                 (a.pk is None and a.exigido.codigo == anexo_id)), None)
            if seleccionado is None:
                raise Http404('Anexo fuera de la entrega seleccionada.')
        from apps.documentos.presentation.expediente_archivos import servir_version, versiones_del_documento
        if request.GET.get('archivo'):
            return servir_version(request, seleccionado, request.GET['archivo'])
        if request.GET.get('borrador') == '1':
            from apps.documentos.presentation.documentos_entrega import borrador_actual
            return borrador_actual(request, seleccionado)
        vista = request.GET.get('vista', '')
        if vista not in ('gestion', 'observaciones', 'versiones', 'anexos'):
            vista = 'observaciones' if request.GET.get('paso') == 'evaluacion' else 'gestion'
        if anexo_id:
            vista = 'versiones'
        contexto.update(gestion_documento=elegida, entrega=elegida, en_gestion_documento=True,
                        documento=seleccionado, nombre=seleccionado.nombre_documental if anexo_id else elegida['nombre'],
                        papel=elegida.get('papel', ''), volver=destino,
                        evaluaciones_previas=elegida.get('evaluaciones_previas', []),
                        vista_documento=vista,
                        versiones_archivo=(versiones_del_documento(seleccionado)
                                           if vista == 'versiones' else []),
                        ruta_expediente=reverse('gestion_expediente_unidad', args=[slug]),
                        ruta_archivos=destino + '&' + urlencode({'gestionar': seleccion}) +
                                      (f'&anexo={seleccionado.pk}' if anexo_id else ''),
                        superficie_unidad=True)
        from apps.documentos.presentation.documentos_entrega import ruta_borrador
        contexto['borrador_url'] = ruta_borrador(seleccionado)
        contexto['periodo'] = next((p for p in contexto['periodos']
                                    if p['corte'] == elegida['documento'].corte), None)
        if request.GET.get('fragment') == '1':
            if vista == 'observaciones':
                from .observaciones_documentales import contexto_observaciones
                contexto['observaciones_documentales'] = contexto_observaciones(seleccionado, request.user)
            return render(request, 'portal/pages/unidades/gestion/includes/expediente_gestion_documento.html', contexto)
        if vista == 'observaciones':
            from .observaciones_documentales import contexto_observaciones
            contexto['observaciones_documentales'] = contexto_observaciones(seleccionado, request.user)
    return render(request, 'portal/pages/unidades/gestion/expediente.html', contexto)
