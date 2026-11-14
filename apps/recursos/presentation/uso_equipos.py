"""Uso acreditado de cada activo físico, separado de lo solicitado.

Una solicitud o un cierre incompleto no demuestra que un equipo se utilizó.
Las horas salen del horario y asistencia reales y de los equipos conservados
en el cierre; las franjas simultáneas del mismo activo se cuentan una vez.
"""
import json
from collections import defaultdict
from datetime import timedelta

from django.db.models import Max, Min
from django.utils import timezone

from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.recursos.models.redistribucion import PoliticaUsoEquipo
from apps.reservas.models.reservas import Reserva
from apps.recursos.presentation.utilizacion import _execution_values, _registrada_al_corte

MUCHO_USO_HORAS = 500
FUERA_DE_SERVICIO = ('mantenimiento', 'dañado', 'no_disponible', 'obsoleto', 'no_localizado')

SITUACIONES = {
    'en_uso': ('Uso acreditado', 'is-ok', 'fas fa-check-circle'),
    'demandado': ('Uso acreditado alto', 'is-uso', 'fas fa-fire'),
    'poco_uso': ('Poco uso acreditado', 'is-uso', 'fas fa-hourglass-half'),
    'sin_uso': ('Sin uso acreditado en el plazo definido', 'is-fuera', 'fas fa-bell'),
    'sin_registros': ('Sin uso acreditado · revisar registros', 'is-fuera', 'fas fa-bell'),
    'pendiente': ('Cierres por completar · uso sin verificar', 'is-uso', 'fas fa-exclamation-circle'),
    'nuevo': ('Recién llegado · programar su uso', 'is-nuevo', 'fas fa-seedling'),
    'fuera': ('Fuera de servicio', 'is-gris', 'fas fa-tools'),
}


def politica_uso():
    """Configuración explícita, sin crear filas ni presumir valores vigentes."""
    registro = PoliticaUsoEquipo.objects.filter(pk=1).first()
    dias = registro.dias_sin_uso if registro else None
    horas = float(registro.horas_minimas_anuales) if registro and registro.horas_minimas_anuales is not None else None
    return dict(configurada=dias is not None or horas is not None, dias_sin_uso=dias,
        horas_minimas_anuales=horas, dias_atencion=registro.dias_atencion if registro else None,
        fundamento=registro.fundamento if registro else '')


def _lista(valor):
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (ValueError, TypeError):
            return []
    return valor if isinstance(valor, list) else []


def equipos_reales_reserva(reserva):
    """IDs del cierre y limitaciones; nunca sustituye por equipos solicitados.

    Los IDs físicos son la identidad estable. Sólo una captura sin ID puede
    resolverse por código vigente o alias. Un ID inválido no se rescata con un
    código de otro activo. Es lectura y conserva los IDs aunque cambiara unidad.
    """
    detalle = reserva.detalle_ejecucion if isinstance(reserva.detalle_ejecucion, dict) else {}
    capturados = detalle.get('equipos')
    if not isinstance(capturados, list):
        return dict(ids=[], pendientes=True, motivos=['Cierre sin equipos reales capturados'])
    ids, codigos, motivos = set(), set(), []
    for item in capturados:
        if not isinstance(item, dict):
            motivos.append('Referencia real de equipo inválida')
            continue
        if item.get('id') not in (None, ''):
            try:
                numero = int(item['id'])
                if isinstance(item['id'], bool) or numero <= 0 or str(numero) != str(item['id']).strip():
                    raise ValueError
                ids.add(numero)
            except (TypeError, ValueError):
                motivos.append('ID real de equipo inválido')
        elif item.get('codigo'):
            codigos.add(str(item['codigo']))
        else:
            motivos.append('Equipo real sin identidad')
    existentes = set(UnidadEquipo.objects.filter(pk__in=ids).values_list('pk', flat=True))
    if ids != existentes:
        motivos.append('El cierre refiere un equipo inexistente')
    encontrados = dict(UnidadEquipo.objects.filter(codigo_unidad__in=codigos).values_list('codigo_unidad', 'pk'))
    encontrados.update(AliasCodigoUnidadEquipo.objects.filter(codigo__in=codigos).values_list('codigo', 'unidad_equipo_id'))
    existentes.update(encontrados.values())
    if codigos - encontrados.keys():
        motivos.append('Código real sin correspondencia en inventario')
    return dict(ids=sorted(existentes), pendientes=bool(motivos), motivos=motivos)


def _longitud(intervalos):
    """Un activo físico no produce dos horas por una hora simultánea."""
    fin, total = -1, 0
    for inicio, hasta in sorted(intervalos):
        total += max(0, hasta - max(inicio, fin))
        fin = max(fin, hasta)
    return total


def leer_uso_equipos(desde, codigos=None, *, hasta=None):
    """Lectura trazable sin escrituras, inclusiva hasta el corte indicado.

    Los recursos reales, los solicitados y los cierres incompletos se separan.
    No se reparte una atención entre todos los equipos de un modelo o área.
    """
    hasta = hasta or timezone.localdate()
    vigentes = dict(UnidadEquipo.objects.values_list('pk', 'codigo_unidad'))
    codigos_vigentes = set(vigentes.values())
    alias = dict(AliasCodigoUnidadEquipo.objects.values_list('codigo', 'unidad_equipo__codigo_unidad'))
    permitidos = set(codigos) if codigos is not None else None

    def nombrados(valor, *, filtrar=True):
        resultado = set()
        for item in _lista(valor):
            if not isinstance(item, dict):
                continue
            if item.get('id') not in (None, ''):
                try:
                    numero = int(item['id'])
                    codigo = (vigentes.get(numero) if not isinstance(item['id'], bool)
                              and str(numero) == str(item['id']).strip() else None)
                except (TypeError, ValueError):
                    codigo = None
            else:
                codigo = alias.get(item.get('codigo'), item.get('codigo'))
            if codigo and codigo in codigos_vigentes and (not filtrar or permitidos is None or codigo in permitidos):
                resultado.add(codigo)
        return resultado

    def vacia():
        return dict(horas=0.0, sesiones=0, ultimo=None, fuentes=[], pendientes=[], programadas=[],
                    por_mes=[], por_finalidad=[], por_unidad=[], solapamientos=False)

    uso, intervalos, dias = defaultdict(vacia), defaultdict(list), defaultdict(set)
    sin_equipo = []
    reservas = Reserva.objects.filter(fecha__gte=desde, fecha__lte=hasta,
        estado__in=('completada', 'confirmada', 'en_proceso')).only(
            'pk', 'fecha', 'estado', 'resultado_cierre', 'detalle_ejecucion', 'unidades_seleccionadas',
            'hora_inicio', 'hora_fin', 'laboratorio_id', 'proposito_codigo', 'tipo_solicitud', 'codigo_reserva').order_by('-fecha', '-pk')
    ahora = timezone.localtime()
    for reserva in reservas.iterator():
        seleccionados = nombrados(reserva.unidades_seleccionadas)
        ejecucion = reserva.detalle_ejecucion if isinstance(reserva.detalle_ejecucion, dict) else {}
        reales = nombrados(ejecucion.get('equipos'))
        if reserva.estado != 'completada':
            vencida = reserva.fecha < hasta or (hasta == ahora.date() and reserva.hora_fin and reserva.hora_fin < ahora.time())
            destino = 'pendientes' if vencida else 'programadas'
            for codigo in seleccionados:
                uso[codigo][destino].append(reserva.pk)
            continue
        valores = _execution_values(reserva)
        captura = ejecucion.get('equipos')
        identidades_validas = isinstance(captura, list) and all(
            isinstance(item, dict) and bool(nombrados([item], filtrar=False)) for item in captura)
        valida = (reserva.es_efectiva and valores is not None and valores[2] > 0
                  and _registrada_al_corte(reserva, hasta) and identidades_validas)
        if not valida:
            for codigo in seleccionados | reales:
                uso[codigo]['pendientes'].append(reserva.pk)
            if not isinstance(captura, list) or not identidades_validas:
                sin_equipo.append(dict(reserva_id=reserva.pk, unidad_id=reserva.laboratorio_id,
                                       motivo='Cierre sin identidad válida de equipos reales'))
            continue
        inicio, fin, asistentes = valores
        for codigo in reales:
            fila = uso[codigo]
            fila['sesiones'] += 1
            fila['ultimo'] = max(fila['ultimo'] or reserva.fecha, reserva.fecha)
            fila['fuentes'].append(dict(reserva_id=reserva.pk, codigo=reserva.codigo_reserva,
                fecha=reserva.fecha.isoformat(), unidad_id=reserva.laboratorio_id,
                finalidad=reserva.get_proposito_codigo_display(), tipo=reserva.get_tipo_solicitud_display(),
                inicio=inicio, fin=fin, horas=round((fin - inicio) / 3600, 4), asistentes=asistentes))
            intervalos[(codigo, reserva.fecha)].append((inicio, fin))
            dias[codigo].add(reserva.fecha)
    for codigo, fila in uso.items():
        por_mes = defaultdict(lambda: dict(horas=0.0, sesiones=0))
        por_finalidad = defaultdict(lambda: dict(horas=0.0, sesiones=0))
        por_unidad = defaultdict(lambda: dict(horas=0.0, sesiones=0))
        for dia in dias[codigo]:
            duraciones = intervalos[(codigo, dia)]
            horas = _longitud(duraciones) / 3600
            fila['horas'] += horas
            por_mes[dia.strftime('%Y-%m')]['horas'] += horas
            fila['solapamientos'] |= sum(b - a for a, b in duraciones) > horas * 3600
        for fuente in fila['fuentes']:
            por_mes[fuente['fecha'][:7]]['sesiones'] += 1
        for llave, destino in (('finalidad', por_finalidad), ('unidad_id', por_unidad)):
            grupos = defaultdict(list)
            for fuente in fila['fuentes']:
                grupos[(fuente[llave], fuente['fecha'])].append((fuente['inicio'], fuente['fin']))
                destino[fuente[llave]]['sesiones'] += 1
            for (valor, _), franjas in grupos.items():
                destino[valor]['horas'] += _longitud(franjas) / 3600
        fila['horas'] = round(fila['horas'], 4)
        fila['por_mes'] = [dict(mes=k, **v) for k, v in sorted(por_mes.items())]
        fila['por_finalidad'] = [dict(finalidad=k, **v) for k, v in sorted(por_finalidad.items())]
        fila['por_unidad'] = [dict(unidad_id=k, **v) for k, v in sorted(por_unidad.items())]
    return dict(equipos=dict(uso), incidencias_sin_equipo=sin_equipo, desde=desde, hasta=hasta)


def uso_de_equipos(desde, codigos=None, *, hasta=None):
    """API compatible: horas efectivas y su evidencia, nunca lo previsto."""
    return leer_uso_equipos(desde, codigos, hasta=hasta)['equipos']


def llegadas(equipos):
    """Último traslado o ingreso documentado; ausencia no equivale a antigüedad."""
    equipos = list(equipos)
    traslados = dict(EventoCicloVidaEquipo.objects.filter(equipo__in=equipos, tipo='transferencia')
                     .values('equipo').annotate(ultima=Max('fecha')).values_list('equipo', 'ultima'))
    registros = dict(EventoCicloVidaEquipo.objects.filter(equipo__in=equipos, tipo='registro')
                     .values('equipo').annotate(primera=Min('fecha')).values_list('equipo', 'primera'))
    return {e.pk: (traslados[e.pk].date() if e.pk in traslados else e.fecha_ingreso_bodega or e.fecha_adquisicion
                   or (registros[e.pk].date() if e.pk in registros else None)) for e in equipos}


def situacion(equipo, uso, llegada, hoy=None, *, incidencias_unidad=(), politica=None):
    """Una alerta solicita verificar y corregir; no prueba abandono físico."""
    hoy = hoy or timezone.localdate()
    politica = politica_uso() if politica is None else politica
    dias = politica['dias_sin_uso']
    minimas = politica['horas_minimas_anuales']
    uso = uso or dict(horas=0.0, sesiones=0, ultimo=None)
    pendientes = sorted(set(uso.get('pendientes', [])) | {i['reserva_id'] for i in incidencias_unidad})
    if not equipo.activa or equipo.estado_unidad in FUERA_DE_SERVICIO or equipo.fecha_baja:
        clave = 'fuera'
    elif pendientes:
        clave = 'pendiente'
    elif uso['ultimo'] is None and llegada and (llegada == hoy or dias and (hoy - llegada).days < dias):
        clave = 'nuevo'
    elif uso['ultimo'] is None:
        clave = 'sin_registros'
    elif dias is not None and (hoy - uso['ultimo']).days >= dias:
        clave = 'sin_uso'
    elif minimas is not None and uso['horas'] < minimas and llegada and (hoy - llegada).days >= 365:
        clave = 'poco_uso'
    elif uso['horas'] > MUCHO_USO_HORAS:
        clave = 'demandado'
    else:
        clave = 'en_uso'
    etiqueta, tono, icono = SITUACIONES[clave]
    if clave == 'sin_uso':
        etiqueta = f'Sin uso acreditado en {dias} días'
    institucional = (politica['configurada'] and clave in ('sin_uso', 'poco_uso', 'pendiente')
                     or clave == 'sin_registros' and dias is not None and llegada is not None and (hoy - llegada).days >= dias)
    return dict(clave=clave, etiqueta=etiqueta, tono=tono, icono=icono,
        alerta=clave in ('sin_uso', 'sin_registros', 'poco_uso', 'pendiente'),
        alerta_institucional=bool(institucional), politica=politica,
        horas=round(uso['horas'], 1), sesiones=uso['sesiones'], ultimo=uso['ultimo'], llegada=llegada,
        pendientes=pendientes, fuentes=uso.get('fuentes', []), por_mes=uso.get('por_mes', []),
        por_finalidad=uso.get('por_finalidad', []), por_unidad=uso.get('por_unidad', []),
        programadas=uso.get('programadas', []), solapamientos=uso.get('solapamientos', False),
        limite='La ausencia de cierres no prueba falta de uso físico; confirma registros y causas antes de reasignar.')


def situaciones(equipos, hoy=None):
    """Lectura inmediata de todo activo solicitado, sin crear ni cerrar alertas."""
    hoy = hoy or timezone.localdate()
    equipos = list({e.pk: e for e in equipos}.values())
    politica = politica_uso()
    lectura = leer_uso_equipos(hoy - timedelta(days=365), {e.codigo_unidad for e in equipos}, hasta=hoy)
    desde_cuando = llegadas(equipos)
    por_unidad = defaultdict(list)
    for incidencia in lectura['incidencias_sin_equipo']:
        por_unidad[incidencia['unidad_id']].append(incidencia)
    return {e.pk: situacion(e, lectura['equipos'].get(e.codigo_unidad), desde_cuando.get(e.pk), hoy,
                           incidencias_unidad=por_unidad[e.laboratorio_id], politica=politica) for e in equipos}
