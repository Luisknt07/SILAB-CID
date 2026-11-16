"""Validación técnica conservadora de anexos nativos de laboratorios.

Es una lectura por unidad y período, reutilizable entre documentos. No cambia
estados, notas, firmas ni aprobaciones y no debe instanciarse por fila de un GET.
La ausencia de hallazgos permite el paso técnico al motor que gestione la entrega;
no afirma calidad académica ni cumplimiento normativo de documentos externos.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.respaldo_medicion import faltantes_desecho, validar_respaldo
from apps.documentos.presentation.cumplimiento_practicas import conteos_del_periodo
from apps.documentos.presentation.aprobacion_tecnica_laboratorios import (
    ENTIDADES, ESQUEMA_APROBACION, capturas_tecnicas, huella_captura,
)
from apps.documentos.presentation.funcionalidad_laboratorios import funcionalidad_documentada
from apps.documentos.presentation.infraestructura_laboratorios import infraestructura_documentada
from apps.documentos.presentation.medicion_metas import (
    evidencias_verificadas, inspecciones_documentadas, registros_de_gestion, resultados_documentados,
)
from apps.documentos.presentation.perfil_unidades import es_unidad_auditable


VERSION_REGLAS = 3
# Código, fuente y padre son deliberadamente explícitos. Un catálogo personalizado
# no recibe una aprobación implícita por compartir una categoría de reporte.
# Desde documentos.0025 el informe lleva cinco anexos y cada uno se revisa entero:
# - prácticas: planificación, ejecución y guías;
# - seguridad: inducciones, inspecciones y desechos;
# - equipamiento: mantenimiento, funcionalidad, inventario e insumos;
# - investigación: resultados y transferencia.
# Los anexos retirados ya no se revisan solos. La versión no cambia: la huella del
# uso sigue vigente y la de los anexos fusionados cambia porque leen más fuentes.
FUENTES_STOCK = {
    'REGISTRO-USO': ('reservas', 'INFORME-SEMESTRAL'),
    'PRACTICAS-FT02': ('planificaciones', 'INFORME-SEMESTRAL'),
    'INDUCCION-SEGURIDAD': ('seguridad', 'INFORME-SEMESTRAL'),
    'EQUIPAMIENTO': ('equipamiento', 'INFORME-SEMESTRAL'),
    'INVESTIGACION': ('investigacion', 'INFORME-SEMESTRAL'),
}


def _json_seguro(valor):
    if isinstance(valor, dict):
        return {str(k): _json_seguro(v) for k, v in sorted(valor.items(), key=lambda par: str(par[0]))
                if k not in ('calculado_en', 'consultado_en', 'dentro_plazo')}
    if isinstance(valor, (list, tuple)):
        return [_json_seguro(v) for v in valor]
    if isinstance(valor, set):
        return sorted((_json_seguro(v) for v in valor), key=str)
    if isinstance(valor, (date, datetime, time)):
        return valor.isoformat()
    if isinstance(valor, (Decimal, UUID)):
        return str(valor)
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    raise TypeError(f'Fuente no serializable: {type(valor).__name__}')


def _porcentaje(numerador, denominador):
    return round(min(100, max(0, 100 * numerador / denominador)), 2) if denominador else None


def _vigentes(filas):
    """Las filas de resultados que no están anuladas."""
    return [fila for fila in filas if fila['estado'] != 'anulado']


def _dia(valor):
    return (timezone.localtime(valor) if timezone.is_aware(valor) else valor).date()


class ContextoCalidad:
    def __init__(self, unidad, inicio, fin):
        self.unidad, self.inicio, self.fin = unidad, inicio, fin
        self.corte = min(fin, timezone.localdate())
        self._cache = {}

    def _una_vez(self, clave, cargar):
        if clave not in self._cache:
            self._cache[clave] = cargar()
        return self._cache[clave]

    def _url(self, tipo=None):
        datos = dict(anio=self.inicio.year, corte='B' if self.inicio.month >= 7 else 'A')
        if tipo:
            datos['tipo'] = tipo
        return reverse('fuentes_metas_unidad' if tipo else 'gestion_expediente_unidad',
                       args=[self.unidad.slug]) + '?' + urlencode(datos)

    def _hallazgo(self, lista, regla, mensaje, entidad='', identificador=None, severidad='revision', tipo=None):
        lista.append(dict(regla=regla, severidad=severidad, mensaje=mensaje,
                          url=self._url(tipo), entidad=entidad, id=identificador))

    def _archivo(self, archivo, *, legible=False):
        def cargar():
            if not archivo or not archivo.name:
                return dict(nombre='', sha256='', disponible=False)
            try:
                if legible:
                    return dict(nombre=archivo.name, sha256=validar_respaldo(archivo), disponible=True)
                with archivo.open('rb') as stream:
                    huella = hashlib.file_digest(stream, 'sha256').hexdigest()
                    disponible = stream.tell() > 0
                return dict(nombre=archivo.name, sha256=huella, disponible=disponible)
            except (OSError, ValueError, ValidationError):
                return dict(nombre=archivo.name, sha256='', disponible=False)
        return self._una_vez(('archivo', archivo.name if archivo else '', legible), cargar)

    def _gestion(self):
        return self._una_vez('gestion', lambda: registros_de_gestion(self.unidad, self.inicio, self.fin))

    def _concretos(self, objeto):
        """Fuente completa de los datos persistidos, sin depender de una lista parcial.

        No se usa sobre cuentas de usuario: de ellas sólo se captura la identidad
        pública que figura en el documento, nunca credenciales ni sesiones.
        """
        return {campo.attname: (self._archivo(getattr(objeto, campo.attname))
                if campo.get_internal_type() in ('FileField', 'ImageField')
                else _json_seguro(getattr(objeto, campo.attname)))
                for campo in objeto._meta.concrete_fields
                if campo.name not in ('actualizado_en', 'fecha_actualizacion', 'updated_at')}

    @staticmethod
    def _identidad(usuario):
        return dict(id=usuario.pk, username=usuario.get_username(), nombre=usuario.get_full_name()) if usuario else None

    def _evidencias(self):
        return self._una_vez('evidencias', lambda: list(EvidenciaGestionUnidad.objects.filter(
            unidad=self.unidad, fecha__range=(self.inicio, self.corte)).select_related('recurso', 'responsable')))

    def _verificadas(self):
        return self._una_vez('verificadas', lambda: {e.pk for e in evidencias_verificadas(
            self.unidad, self._evidencias(), self.inicio, self.corte)})

    def _control_evidencias(self, tipos, hallazgos):
        filas = [e for e in self._evidencias() if e.tipo in tipos and e.estado != 'anulado']
        verificadas = self._verificadas() if filas else set()
        for e in filas:
            if e.demostracion:
                self._hallazgo(hallazgos, 'FUENTE_DEMO', 'La fuente está identificada como demostración.',
                               e._meta.label, e.pk, 'bloqueo', e.tipo)
            elif e.pk not in verificadas:
                self._hallazgo(hallazgos, 'FUENTE_SIN_VERIFICAR',
                    'La evidencia está incompleta, sin verificar o cambió respecto de su auditoría.',
                    e._meta.label, e.pk, 'bloqueo', e.tipo)
        return [dict(id=e.pk, codigo=e.codigo, tipo=e.tipo, fecha=e.fecha, estado=e.estado,
            demostracion=e.demostracion, detalle=e.detalle, alcance=e.alcance,
            responsable=e.responsable_id, recurso=e.recurso_id,
            sha256=e.recurso.hash_sha256 if e.recurso_id else '', enlace=e.enlace)
            for e in filas]

    def _conciliacion(self, tipo, hallazgos):
        lectura = self._gestion().get('mediciones_porcentuales', {}).get(tipo)
        medida = dict(lectura) if lectura else {}
        medida['evidencias_control'] = self._control_evidencias({tipo}, hallazgos)
        ids_reales = {e.pk for e in self._evidencias() if e.tipo == tipo and
                      e.pk in self._verificadas() and not e.demostracion}
        if any(f.get('evidencia') not in ids_reales for f in medida.get('fuentes', [])):
            self._hallazgo(hallazgos, 'CONCILIACION_SIN_FUENTE_REAL',
                'El universo conciliado no conserva una fuente real verificada del contexto.', tipo=tipo)
        if not medida or medida.get('pendiente') or not medida.get('fuentes'):
            self._hallazgo(hallazgos, 'UNIVERSO_SIN_CONCILIAR',
                (medida or {}).get('motivo') or 'Falta una fuente independiente que confirme todo el universo del período.',
                tipo=tipo)
        elif medida['numerador'] != medida['denominador']:
            self._hallazgo(hallazgos, 'COBERTURA_INCOMPLETA',
                'Los registros no cubren el total observado y conciliado.', tipo=tipo)
        return medida or {}

    def _sesiones(self):
        def cargar():
            from apps.reservas.models.reservas import Reserva
            from apps.formacion.models.practicas import PlanificacionPractica, EjecucionPractica
            reservas = list(Reserva.objects.filter(laboratorio=self.unidad,
                fecha__range=(self.inicio, self.fin)).exclude(estado__in=('cancelada', 'rechazada', 'vencida'))
                .only('pk', 'fecha', 'estado', 'proposito_codigo', 'subtipo_actividad',
                      'resultado_cierre', 'detalle_ejecucion'))
            planes = list(PlanificacionPractica.objects.filter(unidad=self.unidad,
                fecha__range=(self.inicio, self.fin), eliminado_en__isnull=True, es_version_vigente=True)
                .exclude(estado='archivada').values('pk', 'codigo', 'reserva_id', 'fecha', 'estado'))
            ejecuciones = list(EjecucionPractica.objects.filter(planificacion__unidad=self.unidad,
                eliminado_en__isnull=True, planificacion__eliminado_en__isnull=True)
                .filter(Q(fecha_ejecucion__range=(self.inicio, self.fin)) |
                        Q(planificacion_id__in=[p['pk'] for p in planes]))
                .values('pk', 'planificacion_id', 'fecha_ejecucion', 'estado', 'resultado'))
            return reservas, planes, ejecuciones
        return self._una_vez('sesiones', cargar)

    def _aprobaciones(self, datos, grupo, hallazgos):
        fuentes = datos.get('fuentes_practicas', {})
        ids = {g: [f['id'] for f in fuentes.get(g, [])] for g in ENTIDADES}
        ids['planificaciones'] = sorted(set(ids['planificaciones']) | {
            p['plan'] for g in fuentes.get('guias', []) for p in g.get('vinculos_academicos', [])})
        capturas = self._una_vez('capturas_aprobacion', lambda: capturas_tecnicas(self.unidad, ids))
        def cargar():
            from apps.formacion.models.practicas import RegistroAuditoriaUnidad
            filtro = Q(pk__in=[])
            for g, entidad in ENTIDADES.items():
                filtro |= Q(entidad=entidad, objeto_id__in=[str(i) for i in ids[g]])
            filas = RegistroAuditoriaUnidad.objects.filter(filtro, unidad=self.unidad, accion='aprobar',
                datos_nuevos__aprobacion_tecnica__esquema=ESQUEMA_APROBACION).order_by('pk')
            return {(a.entidad, a.objeto_id): a for a in filas}
        aprobaciones = self._una_vez('auditorias_aprobacion', cargar)
        salida = []
        for fuente in fuentes.get(grupo, []):
            clave = (ENTIDADES[grupo], str(fuente['id']))
            actual, evento = capturas.get(clave), aprobaciones.get(clave)
            sello = evento.datos_nuevos.get('aprobacion_tecnica', {}) if evento else {}
            campos = actual['campos'] if actual else {}
            actor_campo, fecha_campo = (('revisado_por_id', 'revisado_en') if grupo == 'planificaciones' else
                ('validado_por_id', 'validado_en') if grupo == 'ejecuciones' else ('aprobado_por_id', 'aprobado_en'))
            huella = huella_captura(actual) if actual else ''
            coincide = bool(evento and actual and sello.get('unidad') == self.unidad.pk and
                sello.get('entidad') == clave[0] and sello.get('objeto') == fuente['id'] and
                sello.get('actor') == evento.usuario_id == campos.get(actor_campo) and evento.usuario_id and
                sello.get('aprobado_en') == campos.get(fecha_campo) and
                sello.get('sha256') == huella == huella_captura(sello.get('captura')) and
                _dia(evento.creado_en) <= self.corte)
            if not coincide:
                self._hallazgo(hallazgos, 'APROBACION_TECNICA_NO_VERIFICABLE',
                    'La aprobación es anterior al control completo o sus datos, relaciones o archivos cambiaron; '
                    'requiere revisión atribuida de esta versión.', clave[0], fuente['id'])
            elif sello.get('demostracion') is not False:
                self._hallazgo(hallazgos, 'APROBACION_TECNICA_DEMO',
                    'La aprobación se registró como demostración y no acredita gestión real.',
                    clave[0], fuente['id'], 'bloqueo')
            salida.append(dict(entidad=clave[0], id=fuente['id'], evento=evento.pk if evento else None,
                actor=evento.usuario_id if evento else None, fecha=evento.creado_en if evento else None,
                sha256_actual=huella, sha256_aprobado=sello.get('sha256', ''), coincide=coincide,
                demostracion=sello.get('demostracion')))
        if grupo == 'guias':
            # El vínculo académico puede nacer al planificar otra sesión con
            # una guía reutilizada. Lo acredita la revisión técnica de esa planificación,
            # que congela tema, syllabus y guía exacta: no exige aprobar otra vez
            # el contenido de la guía ni trasladar esa tarea al Director.
            for guia in fuentes.get('guias', []):
                for vinculo in guia.get('vinculos_academicos', []):
                    clave = (ENTIDADES['planificaciones'], str(vinculo['plan']))
                    captura, evento = capturas.get(clave), aprobaciones.get(clave)
                    sello = evento.datos_nuevos.get('aprobacion_tecnica', {}) if evento else {}
                    campos = captura['campos'] if captura else {}
                    valida = bool(evento and captura and campos.get('guia_id') == guia['id'] and
                        campos.get('estado') == 'aprobada' and sello.get('unidad') == self.unidad.pk and
                        sello.get('entidad') == clave[0] and sello.get('objeto') == vinculo['plan'] and
                        sello.get('actor') == evento.usuario_id == campos.get('revisado_por_id') and evento.usuario_id and
                        sello.get('aprobado_en') == campos.get('revisado_en') and
                        sello.get('sha256') == huella_captura(captura) == huella_captura(sello.get('captura')) and
                        sello.get('demostracion') is False and _dia(evento.creado_en) <= self.corte)
                    if not valida:
                        self._hallazgo(hallazgos, 'VINCULO_SYLLABUS_SIN_REVISION',
                            'El vínculo de esta guía con asignatura, tema y resultado no conserva una '
                            'planificación con revisión técnica coincidente.', clave[0], vinculo['plan'])
                    salida.append(dict(entidad=clave[0], id=vinculo['plan'], guia=guia['id'],
                        evento=evento.pk if evento else None, sha256_actual=huella_captura(captura) if captura else '',
                        sha256_aprobado=sello.get('sha256', ''), coincide=valida))
        return salida

    def _practicas(self, hallazgos):
        """El anexo de prácticas entero: planificación aprobada, ejecución validada y guías vigentes.

        Su cumplimiento es la parte de esos registros con respaldo completo.
        """
        datos = self._una_vez('practicas', lambda: conteos_del_periodo(self.unidad, self.inicio, self.fin))
        diagnosticos, aprobaciones = {}, {}
        for grupo, entidad in (('planificaciones', 'planificaciones'), ('practicas', 'ejecuciones'), ('guias', 'guias')):
            diagnosticos[grupo] = datos['diagnostico_' + grupo]
            aprobaciones[entidad] = self._aprobaciones(datos, entidad, hallazgos)
            for fila in diagnosticos[grupo]:
                if not fila['cumple']:
                    self._hallazgo(hallazgos, 'RESPALDO_PRACTICA_INCOMPLETO', '; '.join(fila['faltantes']),
                                   grupo, fila['id'], 'bloqueo')
        for fila in datos.get('fuentes_practicas', {}).get('planificaciones', []):
            if fila['estado'] == 'aprobada' and not (fila.get('revisado_por') and fila.get('revisado_en')):
                self._hallazgo(hallazgos, 'FT02_APROBACION_SIN_RESPONSABLE',
                    'La aprobación de la planificación no identifica a quien la revisó y cuándo.',
                    'formacion.PlanificacionPractica', fila['id'])
        reservas, planes, ejecuciones = self._sesiones()
        por_reserva = {p['reserva_id']: p for p in planes if p['reserva_id']}
        ejecutados = {e['planificacion_id'] for e in ejecuciones}
        for reserva in reservas:
            docente = reserva.proposito_codigo == 'docencia_practica' or reserva.subtipo_actividad in (
                'practica_curricular', 'simulacion_demostracion', 'practica_evaluativa')
            if not docente:
                continue
            plan = por_reserva.get(reserva.pk)
            if not plan:
                self._hallazgo(hallazgos, 'SESION_SIN_FT02',
                               'La sesión docente no tiene una planificación de práctica vigente del período.',
                               reserva._meta.label, reserva.pk, 'bloqueo')
            elif reserva.fecha <= self.corte and reserva.es_efectiva and plan['pk'] not in ejecutados:
                self._hallazgo(hallazgos, 'SESION_ATENDIDA_SIN_FT03',
                               'La sesión atendida no tiene registrada la ejecución de la práctica.',
                               reserva._meta.label, reserva.pk, 'bloqueo')
        for e in ejecuciones:
            if e['fecha_ejecucion'] > self.corte:
                self._hallazgo(hallazgos, 'EJECUCION_FUTURA', 'Se registró una ejecución con fecha futura.',
                               'formacion.EjecucionPractica', e['pk'], 'bloqueo')
        todas = [fila for filas in diagnosticos.values() for fila in filas]
        universo_uso = None
        if not todas:
            medida = self._conciliacion('USO', hallazgos)
            universo_uso = medida
            if medida.get('denominador'):
                self._hallazgo(hallazgos, 'ANEXO_VACIO_CON_ACTIVIDAD',
                    'El anexo está vacío, pero existe actividad que requiere comprobar su aplicabilidad.')
        porcentaje = _porcentaje(sum(f['cumple'] for f in todas), len(todas))
        return porcentaje, dict(
            diagnosticos=diagnosticos, fuentes=datos.get('fuentes_practicas', {}), universo_uso=universo_uso,
            aprobaciones=aprobaciones,
            sesiones=[dict(id=r.pk, fecha=r.fecha, estado=r.estado, proposito=r.proposito_codigo,
                           cierre=r.resultado_cierre, ejecucion=r.detalle_ejecucion) for r in reservas],
            planes=planes, ejecuciones=ejecuciones)

    def _equipos(self):
        def cargar():
            from apps.documentos.models.funcionalidad import equipos_del_alcance
            return list(equipos_del_alcance(self.unidad).filter(activa=True, fecha_baja__isnull=True)
                        .select_related('equipo').order_by('pk'))
        return self._una_vez('equipos', cargar)

    def _insumos(self, hallazgos):
        def cargar():
            from apps.recursos.models.consumibles import Consumible, LoteConsumible
            return (list(Consumible.objects.filter(unidad=self.unidad, activo=True).order_by('pk')),
                    list(LoteConsumible.objects.filter(consumible__unidad=self.unidad,
                        consumible__activo=True).select_related('equipo_en_uso').order_by('pk')))
        insumos, lotes = self._una_vez('insumos', cargar)
        por_insumo = defaultdict(list)
        for lote in lotes:
            por_insumo[lote.consumible_id].append(lote)
            mensajes = []
            if lote.cantidad_actual < 0 or lote.cantidad_actual > lote.cantidad_inicial:
                mensajes.append('Saldo del lote incompatible con la cantidad recibida.')
            if lote.cantidad_actual > 0 and lote.estado in ('agotado', 'caducado', 'extraviado', 'retirado'):
                mensajes.append('Lote cerrado con saldo disponible.')
            if lote.cantidad_actual > 0 and lote.fecha_vencimiento and lote.fecha_vencimiento < self.corte:
                mensajes.append('Lote vencido que conserva saldo disponible.')
            if lote.cantidad_actual > 0 and not lote.documento_recepcion:
                mensajes.append('Falta la referencia de recepción del lote.')
            if lote.cantidad_actual > 0 and not (lote.bodega or lote.equipo_en_uso_id):
                mensajes.append('Falta ubicación física del lote.')
            if lote.estado == 'en_uso' and not lote.equipo_en_uso_id:
                mensajes.append('Lote en uso sin equipo identificado.')
            for mensaje in mensajes:
                self._hallazgo(hallazgos, 'LOTE_INCONSISTENTE', mensaje, lote._meta.label, lote.pk)
        for insumo in insumos:
            fisicos = por_insumo[insumo.pk]
            if not insumo.ubicacion or not insumo.unidad_medida:
                self._hallazgo(hallazgos, 'INSUMO_SIN_DATOS', 'Falta ubicación o unidad de medida.', insumo._meta.label, insumo.pk)
            if insumo.stock_total < 0 or (fisicos and sum(lote.cantidad_actual for lote in fisicos) != insumo.stock_total):
                self._hallazgo(hallazgos, 'SALDO_NO_CONCILIADO', 'El saldo general es negativo o difiere de los lotes.',
                               insumo._meta.label, insumo.pk, 'bloqueo')
            elif insumo.stock_total > 0 and not fisicos:
                self._hallazgo(hallazgos, 'EXISTENCIA_SIN_LOTE', 'El saldo no tiene lotes físicos localizables.',
                               insumo._meta.label, insumo.pk)
            if insumo.clasificacion == 'reactivo' and not self._archivo(insumo.ficha_tecnica)['disponible']:
                self._hallazgo(hallazgos, 'REACTIVO_SIN_FICHA', 'Falta ficha técnica o de seguridad disponible del reactivo.',
                               insumo._meta.label, insumo.pk)
        from apps.recursos.models.consumibles import EntradaInventario
        movimientos = self._una_vez('movimientos_inventario', lambda: list(EntradaInventario.objects.filter(
            Q(unidad=self.unidad) | Q(consumible__unidad=self.unidad), fecha__date__range=(self.inicio, self.fin))
            .select_related('consumible', 'usuario').distinct().order_by('fecha', 'pk')))
        for movimiento in movimientos:
            if _dia(movimiento.fecha) > self.corte:
                self._hallazgo(hallazgos, 'MOVIMIENTO_FUTURO', 'Hay movimientos contables con fecha futura.',
                    movimiento._meta.label, movimiento.pk, 'bloqueo')
            if movimiento.unidad_id not in (None, self.unidad.pk) or movimiento.consumible.unidad_id != self.unidad.pk:
                self._hallazgo(hallazgos, 'MOVIMIENTO_FUERA_ALCANCE',
                    'La unidad del movimiento no coincide con la existencia que modifica.',
                    movimiento._meta.label, movimiento.pk, 'bloqueo')
        return dict(insumos=[dict(id=i.pk, codigo=i.codigo, saldo=i.stock_total, unidad=i.unidad_medida,
            ubicacion=i.ubicacion, clasificacion=i.clasificacion, ficha=self._archivo(i.ficha_tecnica),
            datos=self._concretos(i)) for i in insumos],
            lotes=[dict(id=lote.pk, consumible=lote.consumible_id, codigo=lote.codigo, inicial=lote.cantidad_inicial,
                actual=lote.cantidad_actual, estado=lote.estado, bodega=lote.bodega, equipo=lote.equipo_en_uso_id,
                vence=lote.fecha_vencimiento, recepcion=lote.documento_recepcion, datos=self._concretos(lote),
                equipo_datos=self._concretos(lote.equipo_en_uso) if lote.equipo_en_uso_id else None) for lote in lotes],
            movimientos=[dict(datos=self._concretos(m), consumible=self._concretos(m.consumible),
                usuario=self._identidad(m.usuario)) for m in movimientos])

    def _inventario(self, hallazgos):
        fuentes = dict(evidencias=self._control_evidencias({'INVENTARIO'}, hallazgos))
        reales = [e for e in self._evidencias() if e.tipo == 'INVENTARIO' and
                  e.pk in self._verificadas() and not e.demostracion]
        if not reales:
            self._hallazgo(hallazgos, 'FALTA_ACTA_INTEGRAL', 'Falta acta integral real verificada del período.', tipo='INVENTARIO')
        for e in reales:
            if not e.recurso_id:
                self._hallazgo(hallazgos, 'ACTA_SOLO_ENLACE', 'El acta integral necesita un archivo institucional verificable.',
                               e._meta.label, e.pk, tipo='INVENTARIO')
        fuentes['equipos'] = []
        for equipo in self._equipos():
            faltantes = [etq for valor, etq in ((equipo.codigo_bien, 'código del bien'),
                (equipo.custodio, 'custodio'), (equipo.ubicacion_especifica or equipo.ubicacion_bodega, 'ubicación'),
                (equipo.numero_serie, 'serie'), (equipo.existencia_verificada, 'verificación física'),
                (equipo.existencia_verificada_por_id, 'responsable de verificación'),
                (equipo.existencia_verificada_en, 'fecha de verificación')) if not valor]
            if not (equipo.equipo.especificaciones or equipo.equipo.caracteristicas_publicas.strip() or equipo.equipo.ficha_tecnica):
                faltantes.append('información técnica')
            if equipo.equipo.ficha_tecnica and not self._archivo(equipo.equipo.ficha_tecnica)['disponible']:
                faltantes.append('archivo técnico disponible')
            if faltantes:
                self._hallazgo(hallazgos, 'EQUIPO_SIN_IDENTIFICACION', 'Falta: ' + ', '.join(faltantes) + '.',
                               equipo._meta.label, equipo.pk)
            fuentes['equipos'].append(dict(id=equipo.pk, codigo=equipo.codigo_unidad, bien=equipo.codigo_bien,
                serie=equipo.numero_serie, custodio=equipo.custodio,
                ubicacion=equipo.ubicacion_especifica or equipo.ubicacion_bodega,
                fisica=equipo.existencia_verificada, verificador=equipo.existencia_verificada_por_id,
                verificado_en=equipo.existencia_verificada_en, criticidad=equipo.criticidad,
                estado=equipo.estado_unidad, ficha=self._archivo(equipo.equipo.ficha_tecnica)))
        from apps.documentos.models.funcionalidad import equipos_del_alcance
        inventario = self._una_vez('inventario_completo', lambda: list(equipos_del_alcance(self.unidad)
            .select_related('equipo', 'existencia_verificada_por')
            .prefetch_related('espacios_asociados', 'laboratorios').order_by('pk')))
        fuentes['registros_equipos'] = [dict(datos=self._concretos(e), catalogo=self._concretos(e.equipo),
            verificador=self._identidad(e.existencia_verificada_por),
            espacios=[self._concretos(s) for s in sorted(e.espacios_asociados.all(), key=lambda s: s.pk)],
            unidades=sorted(u.pk for u in e.laboratorios.all())) for e in inventario]
        from apps.recursos.models.software import SoftwareDisponible
        from apps.gestion_unidades.models.espacios import EspacioReservable
        software = self._una_vez('software', lambda: list(SoftwareDisponible.objects.filter(
            unidad=self.unidad).prefetch_related('equipos_instalados').order_by('pk')))
        for fila in software:
            if fila.licencias_disponibles > fila.licencias_totales:
                self._hallazgo(hallazgos, 'LICENCIAS_INCONSISTENTES', 'Hay más licencias disponibles que licencias totales.',
                               'recursos.SoftwareDisponible', fila.pk, 'bloqueo')
        fuentes['software'] = [dict(datos=self._concretos(s),
            instalaciones=sorted(e.pk for e in s.equipos_instalados.all())) for s in software]
        espacios = self._una_vez('espacios', lambda: list(EspacioReservable.objects.filter(
            unidad=self.unidad).prefetch_related('equipos_asociados').order_by('pk')))
        fuentes['espacios'] = [dict(datos=self._concretos(s),
            equipos=sorted(e.pk for e in s.equipos_asociados.all())) for s in espacios]
        fuentes.update(self._insumos(hallazgos))
        return None, fuentes

    def _mantenimiento(self, hallazgos):
        medida = self._gestion().get('mediciones_porcentuales', {}).get('MANTENIMIENTO', {})
        infra = self._una_vez('infraestructura', lambda: infraestructura_documentada(
            self.unidad, date(self.inicio.year, 1, 1), date(self.inicio.year, 12, 31)))
        fuentes = dict(medicion=medida, infraestructura=infra,
                      evidencias=self._control_evidencias({'PLAN-INFRA', 'EJECUCION-INFRA'}, hallazgos))
        equipos = medida.get('equipos', {})
        # El calendario futuro completo no es una ejecución vencida ni un 100 %
        # sobre cero. Conserva la diferencia aunque la meta figure provisional.
        futuro_conocido = bool(medida.get('programadas_futuras') and not medida.get('denominador') and
            equipos.get('universo_conocido') and not any(equipos.get(k) for k in (
                'equipos_sin_plan', 'equipos_sin_responsable', 'equipos_sin_programacion')) and
            infra.get('alcance_declarado') and not infra.get('alcance_contradictorio') and
            not infra.get('espacios_sin_cobertura'))
        if not medida or (medida.get('pendiente') and not futuro_conocido):
            self._hallazgo(hallazgos, 'MANTENIMIENTO_SIN_UNIVERSO',
                medida.get('motivo') or 'Falta programación crítica y universo verificable.', tipo='PLAN-INFRA')
        for fila in infra.get('planes', []) + infra.get('ejecuciones', []):
            if fila['estado'] == 'anulado':
                continue
            if fila.get('demostracion') or not fila.get('verificada'):
                self._hallazgo(hallazgos, 'PLAN_INFRA_SIN_FUENTE_REAL',
                    'El plan o ejecución de infraestructura contiene demostración o verificación pendiente.',
                    'documentos.EvidenciaGestionUnidad', fila['pk'], 'bloqueo', 'PLAN-INFRA')
        for fila in infra.get('espacios_sin_cobertura', []):
            self._hallazgo(hallazgos, 'INFRA_SIN_COBERTURA', 'El espacio no tiene cobertura verificada de mantenimiento.',
                           'gestion_unidades.EspacioReservable', fila['pk'], tipo='PLAN-INFRA')
        for fila in infra.get('pendientes', []):
            if not fila.get('demostracion'):
                self._hallazgo(hallazgos, 'INFRA_EJECUCION_PENDIENTE',
                    'La intervención exigible no conserva ejecución real respaldada.',
                    'documentos.EvidenciaGestionUnidad', fila['plan_id'], tipo='EJECUCION-INFRA')
        if equipos.get('completadas_sin_respaldo') or equipos.get('ordenes_no_acreditables'):
            self._hallazgo(hallazgos, 'ORDENES_SIN_RESPALDO', 'Hay órdenes de mantenimiento con datos o respaldo incompletos.')
        if medida.get('denominador', 0) > medida.get('numerador', 0):
            self._hallazgo(hallazgos, 'MANTENIMIENTO_VENCIDO', 'Hay intervenciones críticas exigibles aún sin ejecución respaldada.')
        return _porcentaje(medida.get('numerador', 0), medida.get('denominador', 0)), fuentes

    def _funcionalidad(self, hallazgos):
        datos = self._una_vez('funcionalidad', lambda: funcionalidad_documentada(self.unidad, self.inicio, self.fin))
        fuentes = dict(funcionalidad=datos, evidencias=self._control_evidencias({'FUNCIONALIDAD'}, hallazgos))
        disponibles = {e.pk for e in self._equipos() if e.estado_unidad in ('disponible', 'en_uso', 'prestado')}
        for fila in datos['ultimas']:
            if fila['pendiente']:
                self._hallazgo(hallazgos, 'EQUIPO_SIN_PRUEBA_FUNCIONAL', 'Falta una prueba funcional real del período.',
                               'recursos.UnidadEquipo', fila['equipo_id'], tipo='FUNCIONALIDAD')
            elif fila['resultado_funcional'] != 'operativo':
                self._hallazgo(hallazgos, 'RESULTADO_FUNCIONAL_ADVERSO',
                    'La prueba funcional documenta observaciones o un resultado no operativo.',
                    'recursos.UnidadEquipo', fila['equipo_id'], tipo='FUNCIONALIDAD')
            if fila['no_apto'] and fila['equipo_id'] in disponibles:
                self._hallazgo(hallazgos, 'NO_OPERATIVO_DISPONIBLE',
                    'El equipo figura disponible o en uso, pero su última prueba real indica no operativo.',
                    'recursos.UnidadEquipo', fila['equipo_id'], 'bloqueo', 'FUNCIONALIDAD')
        # Sin equipos en el alcance, el inventario del mismo anexo dice por qué.
        fuentes['universo_vacio'] = not datos['universo_equipos']
        return None, fuentes  # La comprobación funcional no es un porcentaje global de cumplimiento.

    def _equipamiento(self, hallazgos):
        """El anexo de equipos e inventario entero.

        Revisa el mantenimiento con su medición crítica, la funcionalidad comprobada, el acta
        de revisión física, la identificación de cada equipo y los insumos. Su cumplimiento es
        el del programa crítico de mantenimiento; lo demás aporta hallazgos, no un porcentaje.
        """
        cumplimiento, mantenimiento = self._mantenimiento(hallazgos)
        _sin_porcentaje, funcionalidad = self._funcionalidad(hallazgos)
        _sin_porcentaje, inventario = self._inventario(hallazgos)
        return cumplimiento, dict(funcionalidad, mantenimiento=mantenimiento, inventario=inventario)

    def _seguridad(self, hallazgos):
        datos = self._gestion()
        mensual = datos.get('cobertura_inspecciones', {})
        medida = datos.get('mediciones_porcentuales', {}).get('SEGURIDAD', {})
        inspecciones = self._una_vez('inspecciones', lambda: inspecciones_documentadas(self.unidad, self.inicio, self.fin))
        fuentes = dict(cobertura=mensual, inducciones=medida, inspecciones=inspecciones,
                      evidencias=self._control_evidencias({'INSPECCION'}, hallazgos))
        if not mensual or mensual.get('vencidos_sin_revision'):
            self._hallazgo(hallazgos, 'CONTROL_MENSUAL_FALTANTE', 'Faltan inspecciones reales verificadas de meses ya exigibles.', tipo='INSPECCION')
        if not medida or medida.get('pendiente') or medida.get('numerador', 0) < medida.get('denominador', 0):
            self._hallazgo(hallazgos, 'INDUCCION_INCOMPLETA', medida.get('motivo') or 'Falta inducción verificable de usuarios nuevos.')
        for fila in inspecciones['filas']:
            if fila['estado'] != 'anulado' and (fila.get('estado_condiciones') == 'no_operar' or
                    fila.get('estado_accion') == 'pendiente'):
                self._hallazgo(hallazgos, 'CONDICION_SEGURIDAD_PENDIENTE', 'Existe una condición insegura o acción correctiva pendiente.',
                               'documentos.EvidenciaGestionUnidad', fila['pk'], 'bloqueo', 'INSPECCION')
        protocolos = self._una_vez('protocolos', lambda: list(DocumentoExpediente.objects.filter(
            unidad=self.unidad, exigido__codigo='PROTOCOLO-BIOSEGURIDAD', anio__lte=self.corte.year)
            .select_related('recurso').order_by('-anio', '-version', '-pk')))
        protocolo = next((p for p in protocolos if p.recurso_id and not (
            (p.cargado_en or p.generado_en) and _dia(p.cargado_en or p.generado_en) > self.corte)), None)
        if (not protocolo or not protocolo.firma_verificada or protocolo.estado != 'validado' or
                (protocolo.validado_en and _dia(protocolo.validado_en) > self.corte)):
            self._hallazgo(hallazgos, 'PROTOCOLO_SIN_VALIDAR', 'Falta protocolo vigente firmado y recibido para el laboratorio.')
        else:
            from apps.documentos.presentation.expediente_archivos import estado_integridad_documental
            integridad = estado_integridad_documental(protocolo, inspeccionar=True)
            if not integridad.get('correspondencia_verificada'):
                self._hallazgo(hallazgos, 'PROTOCOLO_REVISION_PENDIENTE', integridad.get('aviso') or 'Revisa el protocolo externo.')
            fuentes['protocolo'] = dict(id=protocolo.pk, version=protocolo.version, recurso=protocolo.recurso_id,
                firma=protocolo.firma_verificada, estado=protocolo.estado,
                sha256=protocolo.recurso.hash_sha256, integridad=integridad)
        return _porcentaje(medida.get('numerador', 0), medida.get('denominador', 0)), fuentes

    def _desechos(self, hallazgos):
        def cargar():
            from apps.recursos.models.desechos import RegistroDesecho
            return list(RegistroDesecho.objects.filter(unidad=self.unidad, fecha_generacion__lte=self.corte)
                .filter(Q(fecha_generacion__gte=self.inicio) | Q(fecha_entrega__gte=self.inicio) |
                        Q(fecha_entrega__isnull=True) | Q(fecha_entrega__gt=self.corte)).order_by('pk'))
        filas = self._una_vez('desechos', cargar)
        fuentes = []
        for fila in filas:
            faltantes = faltantes_desecho(fila, validar_archivo=True, al_corte=self.corte)
            if faltantes:
                self._hallazgo(hallazgos, 'DESECHO_INCOMPLETO', '; '.join(faltantes), fila._meta.label, fila.pk, 'bloqueo', 'DESECHOS')
            if fila.fecha_entrega and fila.fecha_entrega < fila.fecha_generacion:
                self._hallazgo(hallazgos, 'TRASLADO_ANTERIOR_GENERACION', 'La entrega declarada precede a la generación.',
                               fila._meta.label, fila.pk, 'bloqueo', 'DESECHOS')
            fuentes.append(dict(id=fila.pk, generacion=fila.fecha_generacion, entrega=fila.fecha_entrega,
                clase=fila.clase, cantidad=fila.cantidad, unidad=fila.unidad_medida, etapa=fila.etapa,
                origen=fila.origen, responsable=fila.responsable_id, envase=fila.envase, etiquetado=fila.etiquetado,
                almacen=fila.almacenamiento, gestor=fila.gestor_autorizado, licencia=fila.licencia_gestor,
                manifiesto=fila.manifiesto, archivo=self._archivo(fila.documento)))
        medida = self._conciliacion('DESECHOS', hallazgos)
        return _porcentaje(medida.get('numerador', 0), medida.get('denominador', 0)), dict(
            desechos=fuentes, conciliacion=medida, evidencias=self._control_evidencias({'DESECHOS'}, hallazgos))

    def _seguridad_y_desechos(self, hallazgos):
        """El anexo de seguridad entero: inducciones, inspecciones mensuales, protocolo y desechos.

        Su cumplimiento es el de las inducciones, la meta principal; los desechos aportan sus hallazgos.
        """
        cumplimiento, seguridad = self._seguridad(hallazgos)
        _porcentaje_desechos, desechos = self._desechos(hallazgos)
        return cumplimiento, dict(seguridad, desechos=desechos)

    def _investigacion(self, hallazgos):
        """El anexo de investigación y vinculación: resultados y transferencia con su respaldo."""
        propios = []
        _sin, investigacion = self._resultados('INVESTIGACION', propios)
        _sin, transferencia = self._resultados('TRANSFERENCIA', propios)
        if _vigentes(investigacion['resultados']['filas']) or _vigentes(transferencia['resultados']['filas']):
            # Con algo vigente registrado, el vacío de la otra parte no exige declararlo aparte.
            propios = [h for h in propios if h['regla'] != 'RESULTADOS_SIN_DECLARACION']
        hallazgos.extend(propios)
        return None, dict(investigacion=investigacion, transferencia=transferencia)

    def _resultados(self, codigo, hallazgos):
        datos = self._una_vez(('resultados', codigo), lambda: resultados_documentados(self.unidad, self.inicio, self.fin, codigo))
        fuentes = dict(resultados=datos, evidencias=self._control_evidencias({codigo}, hallazgos))
        for fila in datos['filas']:
            if fila['estado'] != 'anulado' and not fila['acredita']:
                self._hallazgo(hallazgos, 'RESULTADO_SIN_RESPALDO_REAL', 'El resultado o entregable no tiene verificación real vigente.',
                               'documentos.EvidenciaGestionUnidad', fila['pk'], 'bloqueo', codigo)
            elif fila['acredita'] and not fila.get('recurso'):
                self._hallazgo(hallazgos, 'RESULTADO_ENLACE_EXTERNO', 'El enlace externo requiere comprobar el producto o la aceptación.',
                               'documentos.EvidenciaGestionUnidad', fila['pk'], tipo=codigo)
        if not _vigentes(datos['filas']):
            # Un registro anulado no es un resultado: el anexo sigue vacío y pide declararse.
            self._hallazgo(hallazgos, 'RESULTADOS_SIN_DECLARACION',
                'No hay resultados registrados; falta comprobar si existían compromisos o declarar la no aplicación.', tipo=codigo)
        # La verificación atribuida al responsable ya revisó producto y aceptación.
        # El anexo nativo los consolida: Dirección no repite esa revisión sin una anomalía.
        return None, fuentes

    def analizar(self, codigo):
        if codigo in self._cache.get('resultados_finales', {}):
            return deepcopy(self._cache['resultados_finales'][codigo])
        hallazgos, fuentes, cumplimiento = [], {}, None
        if not es_unidad_auditable(self.unidad):
            return dict(hallazgos=[], cumplimiento=None, fuentes={}, automatico=False, fuera_alcance=True)
        from apps.documentos.presentation.calidad_automatica_perfiles import analizar_perfil
        perfil = analizar_perfil(self, codigo)
        if perfil is not None:
            resultado = dict(perfil, cumplimiento=None, fuentes=_json_seguro(dict(
                unidad=self.unidad.pk, codigo=codigo, inicio=self.inicio, fin=self.fin,
                corte=self.corte, version_reglas=VERSION_REGLAS, datos=perfil['fuentes'])))
            self._cache.setdefault('resultados_finales', {})[codigo] = resultado
            return deepcopy(resultado)
        catalogo = self._una_vez('catalogo', lambda: {d.codigo: d for d in
            DocumentoExigido.objects.filter(codigo__in=FUENTES_STOCK).select_related('anexo_de')})
        exigido = catalogo.get(codigo)
        esperado = FUENTES_STOCK.get(codigo)
        if (not esperado or not exigido or not exigido.activo or exigido.origen != 'sistema' or
                exigido.fuente_reporte != esperado[0] or not exigido.anexo_de_id or
                exigido.anexo_de.codigo != esperado[1] or not exigido.aplica_a(self.unidad.dependencia,
                    base=getattr(self.unidad, 'codigo_base', self.unidad.dependencia))):
            self._hallazgo(hallazgos, 'DOCUMENTO_NO_AUTOMATIZABLE',
                'Código desconocido, documento externo/narrativo o fuente del catálogo personalizada.')
        elif self.inicio > self.fin or self.inicio > self.corte:
            self._hallazgo(hallazgos, 'PERIODO_NO_MEDIBLE', 'El período es inválido o todavía no empezó.')
        else:
            if (getattr(settings, 'MEDICION_SOLO_DEMO', False) or
                    str(getattr(self.unidad, 'nombre', '')).startswith('[DEMO REPORTES]')):
                self._hallazgo(hallazgos, 'MODO_DEMO', 'El contexto está en modo demostración.', severidad='bloqueo')
            if not getattr(settings, 'MEDICION_METAS_HABILITADA', False):
                self._hallazgo(hallazgos, 'MEDICION_DESACTIVADA', 'La verificación de fuentes reales está desactivada.')
            if codigo == 'PRACTICAS-FT02':
                cumplimiento, fuentes = self._practicas(hallazgos)
            elif codigo == 'REGISTRO-USO':
                medida = self._conciliacion('USO', hallazgos)
                fuentes = dict(conciliacion=medida, evidencias=self._control_evidencias({'USO'}, hallazgos))
                cumplimiento = _porcentaje(medida.get('numerador', 0), medida.get('denominador', 0))
            elif codigo == 'EQUIPAMIENTO':
                cumplimiento, fuentes = self._equipamiento(hallazgos)
            elif codigo == 'INDUCCION-SEGURIDAD':
                cumplimiento, fuentes = self._seguridad_y_desechos(hallazgos)
            elif codigo == 'INVESTIGACION':
                cumplimiento, fuentes = self._investigacion(hallazgos)
        fuentes = _json_seguro(dict(unidad=self.unidad.pk, codigo=codigo, inicio=self.inicio,
            fin=self.fin, corte=self.corte,
            version_reglas=VERSION_REGLAS,
            catalogo=dict(id=exigido.pk, origen=exigido.origen, fuente=exigido.fuente_reporte,
                          padre=exigido.anexo_de_id, tipos=exigido.tipos_unidad, activo=exigido.activo)
                     if exigido else None, datos=fuentes))
        unicos = {json.dumps(h, sort_keys=True): h for h in hallazgos}
        resultado = dict(hallazgos=[unicos[k] for k in sorted(unicos)], cumplimiento=cumplimiento,
                         fuentes=fuentes, automatico=not hallazgos)
        self._cache.setdefault('resultados_finales', {})[codigo] = resultado
        return deepcopy(resultado)
