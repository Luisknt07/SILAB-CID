"""Carga en cada observatorio sus líneas temáticas, indicadores con ficha y valores verificados, el catálogo de
fuentes, las conexiones automáticas, sus tableros y visores, encuestas y levantamientos, aliados y el calendario
(apps/observatorios/operacion/management/observatorios/).

Se puede repetir: crea lo que falta y no toca lo que el observatorio ya editó (una línea o un indicador se busca por
su código; un aliado o una encuesta, por su nombre; un valor, por indicador, fecha y territorio). Con --reescribir
reemplaza los textos y los valores con los del archivo: si un valor publicado cambia, la corrección queda en el
historial. El calendario solo agrega publicaciones planificadas: nada se marca como publicado desde aquí.
--simular muestra lo que haría.
"""
from collections import Counter
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.observatorios.operacion.management.observatorios.contenidos import MEDIOS, OBSERVATORIOS, SOFTWARE_COMUN, VISITAS, VISORES
from apps.observatorios.operacion.management.observatorios.indicadores_lineas import AJUSTES, ALERTAS_VARIACION, CONECTORES, ENCUESTA_LINEA, FUENTE_DE, FUENTES, LEVANTAMIENTOS, LINEA_DE, NUEVOS, TABLEROS, VISORES_INSTITUCIONALES
from apps.observatorios.operacion.management.observatorios.lineas import LINEAS
from apps.observatorios.operacion.management.observatorios.videos_lineas import VIDEOS_LINEAS
from apps.observatorios.operacion.models.observatorios import AliadoObservatorio, ConectorIndicador, EncuestaObservatorio, FuenteDatos, IndicadorObservatorio, LineaObservatorio, PoliticaDatosObservatorio, PublicacionObservatorio, TableroObservatorio, ValorIndicador, VisorExterno
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad

DECIMALES = ('umbral_bajo', 'umbral_alto', 'alerta_variacion')


def miniatura(url, ancho=1920):
    """La miniatura de Commons del ancho pedido: lo que Wikimedia recomienda para reutilizar sus fotos."""
    base, _, nombre = url.rpartition('/')
    return f"{base.replace('/commons/', '/commons/thumb/', 1)}/{nombre}/{ancho}px-{nombre}"


def _descargar(url, intentos=4):
    """Descarga con un User-Agent que identifica a la plataforma; si Wikimedia limita (429), espera y reintenta."""
    import time
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    for intento in range(intentos):
        try:
            pedido = Request(url, headers={'User-Agent': 'CITT-Laboratorios/1.0 (plataforma universitaria)'})
            with urlopen(pedido, timeout=60) as respuesta:
                return respuesta.read()
        except HTTPError as error:
            if error.code != 429 or intento == intentos - 1:
                raise
            time.sleep(20 * (intento + 1))


def indicadores_de(slug, contenido):
    """Los indicadores del archivo con sus ajustes aplicados, más los nuevos de los ejes temáticos."""
    lista = []
    for datos in contenido.get('indicadores', ()):
        ajuste = dict(AJUSTES.get(datos['codigo'], {}))
        valores = {(valor[1], valor[3]): valor for valor in datos.get('valores', ())}
        valores.update({(valor[1], valor[3]): valor for valor in ajuste.pop('valores', ())})
        lista.append({**datos, **ajuste, 'valores': list(valores.values()),
                      'linea': LINEA_DE.get(datos['codigo']), 'fuente_datos': FUENTE_DE.get(datos['codigo'])})
    lista += list(NUEVOS.get(slug, ()))
    # El criterio de variación y su mensaje, salvo que el indicador ya traiga un mensaje por su umbral.
    return [{**datos, 'alerta_variacion': ALERTAS_VARIACION[datos['codigo']][0],
             'mensaje_alerta': datos.get('mensaje_alerta') or ALERTAS_VARIACION[datos['codigo']][1]}
            if datos['codigo'] in ALERTAS_VARIACION else datos for datos in lista]


def _videos(claves):
    """Los videos verificados de una o varias listas, como líneas «ID | título | canal | qué muestra»."""
    claves = (claves,) if isinstance(claves, str) else claves
    return '\n'.join(' | '.join(video) for clave in claves for video in VIDEOS_LINEAS.get(clave, ()))


class Command(BaseCommand):
    help = 'Carga líneas, indicadores, fuentes, conexiones, tableros, encuestas y calendario de los observatorios.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría y no guarda nada.')
        parser.add_argument('--reescribir', action='store_true', help='Reemplaza textos y valores con los del archivo.')
        parser.add_argument('--medios', action='store_true',
                            help='Descarga la portada (Wikimedia Commons) y fija el video de quien no los tiene.')

    @transaction.atomic
    def handle(self, *args, **options):
        self.reescribir = options['reescribir']
        resumen = Counter()
        self.fuentes = {clave: self._fuente(datos, resumen) for clave, datos in FUENTES.items()}
        for slug, contenido in OBSERVATORIOS.items():
            unidad = Unidad.objects.filter(slug=slug, dependencia='observatorios').first()
            if unidad is None:
                self.stdout.write(self.style.WARNING(f'Omitido: {slug} (no está registrado; corra reorganizar_unidades).'))
                continue
            self.lineas = {datos['codigo']: self._linea(unidad, orden, datos, resumen)
                           for orden, datos in enumerate(LINEAS.get(slug, ()), start=1)}
            for orden, datos in enumerate(indicadores_de(slug, contenido), start=1):
                self._indicador(unidad, orden, datos, resumen)
            encuestas = [{**datos, 'linea': ENCUESTA_LINEA.get(datos['nombre'])} for datos in contenido.get('encuestas', ())]
            for orden, datos in enumerate(encuestas + list(LEVANTAMIENTOS.get(slug, ())), start=1):
                self._por_nombre(EncuestaObservatorio, unidad, orden, datos, resumen, ('encuestas nuevas', 'encuestas actualizadas'))
            for orden, datos in enumerate(contenido.get('aliados', ()), start=1):
                self._por_nombre(AliadoObservatorio, unidad, orden, datos, resumen, ('aliados nuevos', 'aliados actualizados'))
            for tipo, titulo, periodo, fecha in contenido.get('publicaciones', ()):
                _publicacion, nueva = PublicacionObservatorio.objects.get_or_create(
                    unidad=unidad, titulo=titulo,
                    defaults={'tipo': tipo, 'periodo': periodo, 'fecha_planificada': date.fromisoformat(fecha)})
                resumen['publicaciones planificadas'] += nueva
            if contenido.get('espacio'):
                self._sala(unidad, contenido['espacio'], resumen)
            for nombre, sitio, descripcion in SOFTWARE_COMUN:
                _programa, nuevo = SoftwareDisponible.objects.get_or_create(
                    unidad=unidad, nombre=nombre,
                    defaults={'sitio_web': sitio, 'descripcion': descripcion, 'tipo_acceso': 'instalacion'})
                resumen['programas nuevos'] += nuevo
            self._tableros(unidad, TABLEROS.get(slug, ()), resumen)
            self._visores(unidad, tuple(VISORES.get(slug, ())) + tuple(VISORES_INSTITUCIONALES.get(slug, ())), resumen)
            resumen['políticas de datos nuevas'] += PoliticaDatosObservatorio.objects.get_or_create(unidad=unidad)[1]
            if options['medios'] and slug in MEDIOS:
                self._medios(unidad, MEDIOS[slug], resumen)
            self.stdout.write(f'Al día: {unidad.nombre}')
        texto = ', '.join(f'{cantidad} {que}' for que, cantidad in sorted(resumen.items()) if cantidad) or 'nada nuevo'
        self.stdout.write(self.style.SUCCESS(f'Observatorios: {texto}.'))
        if options['simular']:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('Simulación: no se guardó nada.'))

    def _medios(self, unidad, medios, resumen):
        """La portada se descarga y se reduce a 1920 px de ancho; se guarda con su crédito. No pisa una portada propia."""
        if not unidad.imagen:
            from io import BytesIO

            from django.core.files.base import ContentFile
            from PIL import Image

            foto = Image.open(BytesIO(_descargar(miniatura(medios['imagen'])))).convert('RGB')
            foto.thumbnail((1920, 1920))
            salida = BytesIO()
            foto.save(salida, 'JPEG', quality=84, optimize=True, progressive=True)
            unidad.imagen.save(f'{unidad.slug}.jpg', ContentFile(salida.getvalue()), save=False)
            unidad.credito_imagen, unidad.credito_imagen_url = medios['credito'], medios['fuente']
            resumen['portadas nuevas'] += 1
        if not unidad.video_unidad and medios.get('video'):
            unidad.video_unidad = medios['video']
            resumen['videos nuevos'] += 1
        unidad.save(update_fields=['imagen', 'credito_imagen', 'credito_imagen_url', 'video_unidad'])

    def _fuente(self, datos, resumen):
        fuente = FuenteDatos.objects.filter(nombre=datos['nombre']).first()
        nuevo = fuente is None
        fuente = fuente or FuenteDatos()
        if self._asignar(fuente, datos, nuevo) or nuevo:
            fuente.full_clean()
            fuente.save()
            resumen['fuentes nuevas' if nuevo else 'fuentes actualizadas'] += 1
        return fuente

    def _linea(self, unidad, orden, datos, resumen):
        datos = {**datos, 'videos': _videos(datos.get('videos', ()))}
        linea = LineaObservatorio.objects.filter(unidad=unidad, codigo=datos['codigo']).first()
        nuevo = linea is None
        linea = linea or LineaObservatorio(unidad=unidad, orden=orden)
        if self._asignar(linea, datos, nuevo) or nuevo:
            linea.full_clean()
            linea.save()
            resumen['líneas nuevas' if nuevo else 'líneas actualizadas'] += 1
        return linea

    def _relacionar(self, objeto, campo, valor):
        """Una línea o una fuente se asigna si falta (o si se pide reescribir); lo que la unidad eligió se respeta."""
        if valor is not None and (self.reescribir or getattr(objeto, f'{campo}_id') is None) \
                and getattr(objeto, f'{campo}_id') != valor.pk:
            setattr(objeto, campo, valor)
            return True
        return False

    def _tableros(self, unidad, tableros, resumen):
        """Los tableros nativos de cada línea, con su vista. Lo que la unidad ajustó no se pisa salvo al reescribir."""
        for orden, (titulo, descripcion, linea, vista, codigos) in enumerate(tableros, start=1):
            tablero, nuevo = TableroObservatorio.objects.get_or_create(
                unidad=unidad, titulo=titulo,
                defaults={'descripcion': descripcion, 'orden': orden, 'vista': vista, 'linea': self.lineas.get(linea)})
            if nuevo or self.reescribir:
                tablero.descripcion, tablero.vista, tablero.linea = descripcion, vista, self.lineas.get(linea)
                tablero.save()
                tablero.indicadores.set(unidad.indicadores_observatorio.filter(codigo__in=codigos))
            resumen['tableros nuevos' if nuevo else 'tableros revisados'] += nuevo or self.reescribir

    def _visores(self, unidad, visores, resumen):
        for orden, datos in enumerate(visores, start=1):
            datos = dict(datos)
            linea = self.lineas.get(datos.pop('linea', None))
            visor = VisorExterno.objects.filter(unidad=unidad, url=datos['url']).first()
            if visor is None:
                visor = VisorExterno(unidad=unidad, orden=orden, linea=linea, **datos)
                visor.full_clean()
                visor.save()
                resumen['visores nuevos'] += 1
            elif self._asignar(visor, {'institucion': datos.get('institucion', '')}, False) | \
                    self._relacionar(visor, 'linea', linea):
                visor.save()
                resumen['visores actualizados'] += 1

    def _sala(self, unidad, datos, resumen):
        """La sala del observatorio: se visita y se usa con una solicitud, no con la agenda de reservas de un
        laboratorio. Las reservas, los consumibles y las cotizaciones quedan apagados siempre; las visitas se
        encienden al crear la sala y después respetan lo que la unidad decidió."""
        sala = EspacioReservable.objects.filter(unidad=unidad, codigo=datos['codigo']).first()
        configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(unidad=unidad)
        if sala is None:
            sala = EspacioReservable(unidad=unidad, tipo='sala', reservable=False, visitable=True, **datos)
            sala.full_clean()
            sala.save()
            resumen['salas nuevas'] += 1
            configuracion.acepta_visitas = True
            configuracion.visitas_texto = configuracion.visitas_texto or VISITAS
        elif sala.reservable:
            sala.reservable = False
            sala.save(update_fields=['reservable'])
        configuracion.reservas_espacios = configuracion.reservas_equipos = configuracion.solicitudes_servicio = False
        configuracion.consumibles = configuracion.cotizacion_costos = False
        configuracion.save()

    def _asignar(self, objeto, datos, nuevo):
        cambio = False
        for campo, valor in datos.items():
            if campo in DECIMALES and valor is not None:
                valor = Decimal(valor)
            actual = getattr(objeto, campo)
            if (nuevo or self.reescribir or actual in ('', None)) and actual != valor:
                setattr(objeto, campo, valor)
                cambio = True
        return cambio

    def _indicador(self, unidad, orden, datos, resumen):
        datos = dict(datos)
        valores = datos.pop('valores', ())
        linea = self.lineas.get(datos.pop('linea', None))
        fuente = self.fuentes.get(datos.pop('fuente_datos', None))
        indicador = IndicadorObservatorio.objects.filter(unidad=unidad, codigo=datos['codigo']).first()
        nuevo = indicador is None
        indicador = indicador or IndicadorObservatorio(unidad=unidad, orden=orden)
        cambio = self._asignar(indicador, datos, nuevo)
        cambio = self._relacionar(indicador, 'linea', linea) | self._relacionar(indicador, 'fuente_datos', fuente) | cambio
        if cambio or nuevo:
            indicador.full_clean()
            indicador.save()
            resumen['indicadores nuevos' if nuevo else 'indicadores actualizados'] += 1
        for periodo, fecha, valor, territorio, provisional, nota in valores:
            registro = ValorIndicador.objects.filter(indicador=indicador, fecha=date.fromisoformat(fecha),
                                                     territorio=territorio).first()
            campos = {'periodo': periodo, 'valor': Decimal(valor), 'provisional': provisional, 'nota': nota}
            if registro is None:
                registro = ValorIndicador(indicador=indicador, fecha=date.fromisoformat(fecha), territorio=territorio,
                                          origen='cargador', **campos)
                registro.full_clean()
                registro.save()
                resumen['valores nuevos'] += 1
            elif self.reescribir and any(getattr(registro, campo) != valor for campo, valor in campos.items()):
                for campo, valor in campos.items():
                    setattr(registro, campo, valor)
                registro.origen = 'cargador'
                registro.save()
                resumen['valores actualizados'] += 1
        if datos['codigo'] in CONECTORES:
            tipo, horas, parametros = CONECTORES[datos['codigo']]
            conector, creado = ConectorIndicador.objects.get_or_create(
                indicador=indicador, defaults={'tipo': tipo, 'frecuencia_horas': horas, 'parametros': parametros})
            if not creado and self.reescribir and (conector.tipo, conector.parametros) != (tipo, parametros):
                conector.tipo, conector.frecuencia_horas, conector.parametros = tipo, horas, parametros
                conector.save()
            resumen['conexiones nuevas'] += creado

    def _por_nombre(self, modelo, unidad, orden, datos, resumen, etiquetas):
        datos = dict(datos)
        linea = self.lineas.get(datos.pop('linea', None))
        objeto = modelo.objects.filter(unidad=unidad, nombre=datos['nombre']).first()
        nuevo = objeto is None
        objeto = objeto or modelo(unidad=unidad, orden=orden)
        cambio = self._asignar(objeto, datos, nuevo)
        if hasattr(objeto, 'linea_id'):
            cambio = self._relacionar(objeto, 'linea', linea) | cambio
        if cambio or nuevo:
            objeto.full_clean()
            objeto.save()
            resumen[etiquetas[0] if nuevo else etiquetas[1]] += 1
