"""Importa medios revisados del FabLab sin red ni sustituciones de fotos locales."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.core.validators import URLValidator

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.models.equipos import EquiposServicios, VideoEquipo
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.identificadores import youtube_id

SLUG = 'laboratorio-fabricacion-digital-prototipado'
MANIFIESTO = Path(__file__).parents[1] / 'catalogos' / 'fablab_medios_2026.json'
TIPOS = {'equipo': EquiposServicios, 'software': SoftwareDisponible, 'consumible': Consumible}
INFORMACION = {
    'equipo': {'descripcion', 'uso_publico', 'instrucciones_publicas', 'especificaciones'},
    'software': {'descripcion', 'instrucciones_acceso', 'sitio_web'},
    'consumible': {'descripcion', 'especificacion_tecnica'},
}
CAMPOS_ENTRADA = {'tipo', 'id', 'codigo', 'identidad', 'imagen', 'limpiar_catalogo', 'videos',
                  'informacion', 'medios_referencia', 'medios_referencia_esperado'}


def vacio(valor):
    return valor is None or valor == '' or valor == {} or valor == []


def combinar(actual, entrante, reemplazar=False):
    """Completa faltantes; listas de medios se identifican por URL, sin borrar otros."""
    resultado = deepcopy(actual)
    for clave, valor in entrante.items():
        previo = resultado.get(clave)
        if isinstance(valor, dict) and isinstance(previo, dict):
            resultado[clave] = combinar(previo, valor, reemplazar)
        elif isinstance(valor, list) and isinstance(previo, list):
            unidos = deepcopy(previo)
            for nuevo in valor:
                indice = next((i for i, viejo in enumerate(unidos)
                               if isinstance(nuevo, dict) and isinstance(viejo, dict)
                               and nuevo.get('url') and nuevo.get('url') == viejo.get('url')), None)
                if indice is not None:
                    unidos[indice] = combinar(unidos[indice], nuevo, reemplazar)
                elif nuevo not in unidos:
                    unidos.append(deepcopy(nuevo))
            resultado[clave] = unidos
        elif vacio(previo) or reemplazar:
            resultado[clave] = deepcopy(valor)
    return resultado


def validar_url(valor):
    URLValidator(schemes=('https', 'http'))(valor)
    url = urlsplit(valor)
    if url.username or url.password:
        raise ValidationError('Las fuentes no admiten credenciales en la URL.')


def validar_svg(archivo):
    """Sólo gráficos estáticos: ni código, documentos incrustados ni referencias externas."""
    from xml.etree import ElementTree
    texto = Path(archivo).read_text(encoding='utf-8-sig')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b|<\?xml-stylesheet\b', texto, re.IGNORECASE):
        raise ValidationError('El SVG contiene declaraciones o estilos externos no permitidos.')
    raiz = ElementTree.fromstring(texto)
    if raiz.tag.rsplit('}', 1)[-1].casefold() != 'svg':
        raise ValidationError('El documento no contiene una imagen SVG.')
    prohibidos = {'script', 'foreignobject', 'iframe', 'object', 'embed',
                  'animate', 'animatemotion', 'animatetransform', 'set', 'discard'}

    def css_seguro(valor):
        valor = re.sub(r'/\*.*?\*/', '', valor, flags=re.DOTALL)
        if re.search(r'@import\b|expression\s*\(', valor, re.IGNORECASE) or '\\' in valor:
            raise ValidationError('El SVG contiene estilos activos o referencias codificadas.')
        referencias = list(re.finditer(r'\burl\s*\((.*?)\)', valor, re.IGNORECASE | re.DOTALL))
        if len(referencias) != len(re.findall(r'\burl\s*\(', valor, re.IGNORECASE)):
            raise ValidationError('El SVG contiene una referencia CSS incompleta.')
        for coincidencia in referencias:
            destino = coincidencia.group(1).strip().strip('\"\'').strip()
            if not re.fullmatch(r'#[A-Za-z0-9_.:-]+', destino):
                raise ValidationError('El SVG contiene una referencia CSS externa.')

    for elemento in raiz.iter():
        etiqueta = elemento.tag.rsplit('}', 1)[-1].casefold()
        if etiqueta in prohibidos:
            raise ValidationError('El SVG contiene elementos activos no permitidos.')
        if etiqueta == 'style':
            css_seguro(''.join(elemento.itertext()))
        for nombre, valor in elemento.attrib.items():
            atributo = nombre.rsplit('}', 1)[-1].casefold()
            if atributo.startswith('on'):
                raise ValidationError('El SVG contiene manejadores de eventos.')
            if atributo == 'base' and valor.strip():
                raise ValidationError('El SVG no puede cambiar la base de sus enlaces.')
            if atributo in {'href', 'src'} and valor.strip() and not re.fullmatch(r'#[A-Za-z0-9_.:-]+', valor.strip()):
                raise ValidationError('El SVG contiene un enlace externo o una URI activa.')
            css_seguro(valor)


def validar_archivo(imagen, tipo):
    ruta = imagen.get('ruta_estatica')
    if not isinstance(ruta, str):
        raise ValidationError('La imagen requiere ruta_estatica.')
    prefijo = 'img/software/oficiales/' if tipo == 'software' else 'img/catalogo/fablab/oficiales/'
    partes = PurePosixPath(ruta).parts
    if (not ruta.startswith(prefijo) or '\\' in ruta or '..' in partes or ':' in ruta
            or str(PurePosixPath(ruta)) != ruta):
        raise ValidationError(f'La imagen debe estar bajo {prefijo}, sin rutas absolutas ni segmentos relativos.')
    if PurePosixPath(ruta).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.avif', '.gif'}:
        raise ValidationError('Formato de imagen no admitido.')
    archivo = finders.find(ruta)
    if not archivo or not Path(archivo).is_file():
        raise ValidationError(f'No existe el archivo estático {ruta}.')
    esperado = imagen.get('sha256', '')
    if not isinstance(esperado, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', esperado):
        raise ValidationError('La imagen requiere SHA256 completo.')
    if hashlib.sha256(Path(archivo).read_bytes()).hexdigest() != esperado.lower():
        raise ValidationError(f'El SHA256 no coincide para {ruta}.')
    try:
        if PurePosixPath(ruta).suffix.lower() == '.svg':
            validar_svg(archivo)
        else:
            from PIL import Image
            with Image.open(archivo) as contenido:
                contenido.verify()
    except Exception as error:
        raise ValidationError(f'El archivo no es una imagen válida: {ruta}.') from error
    for campo in ('fuente', 'credito', 'licencia'):
        if not isinstance(imagen.get(campo), str) or not imagen[campo].strip():
            raise ValidationError(f'La imagen requiere {campo}; no se presume una licencia abierta.')
    validar_url(imagen['fuente'])
    return ruta


def _imagen_actual(objeto, tipo):
    if tipo == 'software':
        metadatos = (objeto.medios_referencia or {}).get('imagen', {})
        if not isinstance(metadatos, dict):
            raise ValidationError('La procedencia de imagen actual requiere revisión antes de sustituir el catálogo.')
        return {'catalogo': objeto.logo_catalogo or '', 'credito': metadatos.get('credito', ''),
                'fuente': metadatos.get('fuente', '')}
    return {'catalogo': objeto.imagen_catalogo or '', 'credito': objeto.credito_imagen or '',
            'fuente': objeto.fuente_imagen or ''}


def _plan_imagen(objeto, tipo, entrada, medios, avisos):
    imagen = entrada.get('imagen')
    limpiar = entrada.get('limpiar_catalogo', False)
    if not isinstance(limpiar, bool):
        raise ValidationError('limpiar_catalogo debe ser un booleano.')
    if imagen is None:
        if limpiar:
            raise ValidationError('Retirar una imagen exige imagen.esperado.')
        return {}, medios
    if not isinstance(imagen, dict):
        raise ValidationError('imagen debe ser un objeto.')
    if limpiar and imagen.get('ruta_estatica'):
        raise ValidationError('No se puede retirar y sustituir una imagen a la vez.')
    ruta = '' if limpiar else validar_archivo(imagen, tipo)
    if getattr(objeto, 'logo' if tipo == 'software' else 'imagen'):
        avisos.append('Foto o logo local protegido; se conserva sin sustitución.')
        return {}, medios
    actual = _imagen_actual(objeto, tipo)
    destino = {'catalogo': ruta, 'credito': '' if limpiar else imagen['credito'],
               'fuente': '' if limpiar else imagen['fuente']}
    if actual == destino:
        if not limpiar:
            medios['imagen'] = combinar(medios.get('imagen') or {},
                                        {k: imagen[k] for k in ('fuente', 'credito', 'licencia')})
        return {}, medios
    if limpiar and not actual['catalogo']:
        return {}, medios  # Una repetición no retira otro medio ni borra metadatos manuales.
    if any(actual.values()) and imagen.get('esperado') != actual:
        raise ValidationError('El catálogo actual no coincide exactamente con imagen.esperado; se conserva.')
    cambios = {'logo_catalogo' if tipo == 'software' else 'imagen_catalogo': ruta}
    if tipo != 'software':
        cambios.update(credito_imagen=destino['credito'], fuente_imagen=destino['fuente'])
    if not limpiar:
        previo = (objeto.medios_referencia or {}).get('imagen') or {}
        conflictos = [k for k in ('fuente', 'credito', 'licencia')
                      if not vacio(previo.get(k)) and previo[k] != imagen[k]]
        if conflictos and 'medios_referencia_esperado' not in entrada:
            raise ValidationError('La procedencia de imagen existente requiere medios_referencia_esperado para sustituirse.')
        medios['imagen'] = {**(medios.get('imagen') or {}),
                            **{k: imagen[k] for k in ('fuente', 'credito', 'licencia')}}
    elif not (objeto.medios_referencia or {}).get('imagen'):
        medios.pop('imagen', None)
    return cambios, medios


def _validar_identidad(objeto, entrada):
    if entrada.get('codigo') != (objeto.codigo or ''):
        raise ValidationError('El código no coincide con el registro seleccionado.')
    identidad = entrada.get('identidad')
    if not isinstance(identidad, dict) or not identidad.get('nombre'):
        raise ValidationError('Se requiere identidad.nombre exacto.')
    for campo in ('nombre', 'marca', 'modelo', 'version'):
        if campo in identidad and str(identidad[campo] or '') != str(getattr(objeto, campo, '') or ''):
            raise ValidationError(f'La identidad {campo} no coincide; no se modifica el recurso.')


def _videos_nuevos(objeto, entrada):
    existentes = {v.youtube_id for v in objeto.videos.all()}
    resultado = []
    for dato in entrada:
        if not isinstance(dato, dict) or any(not isinstance(dato.get(k), str) or not dato[k].strip()
                                             for k in ('titulo', 'canal')):
            raise ValidationError('Cada video requiere título y canal verificables.')
        validar_url(dato.get('url', ''))
        if urlsplit(dato['url']).hostname not in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be',
                                                 'youtube-nocookie.com', 'www.youtube-nocookie.com'}:
            raise ValidationError('El video de manejo debe proceder de YouTube, no de un dominio que copie su identificador.')
        identificador = youtube_id(dato['url'])
        if not identificador:
            raise ValidationError('El video debe identificar un video concreto de YouTube.')
        if identificador in existentes:
            continue
        video = VideoEquipo(equipo=objeto, url='https://www.youtube.com/watch?v=' + identificador,
                            titulo=dato['titulo'], canal=dato['canal'], idioma=dato.get('idioma', 'es'),
                            orden=dato.get('orden', 0))
        video.full_clean()
        resultado.append(video)
        existentes.add(identificador)
    return resultado


class Command(BaseCommand):
    help = 'Importa el manifiesto revisado de medios FabLab; simula salvo --aplicar. No descarga ni crea inventario.'

    def add_arguments(self, parser):
        parser.add_argument('--manifiesto', default=str(MANIFIESTO))
        parser.add_argument('--aplicar', action='store_true')
        parser.add_argument('--informe', help='Guarda el plan completo de cambios como JSON.')

    def handle(self, *args, **opciones):
        try:
            bruto = Path(opciones['manifiesto']).read_bytes()
            manifiesto = json.loads(bruto.decode('utf-8-sig'))
        except (OSError, UnicodeError, ValueError) as error:
            raise CommandError(f'No se pudo leer el manifiesto: {error}') from error
        if not isinstance(manifiesto, dict) or manifiesto.get('version') != 1 or manifiesto.get('unidad') != SLUG:
            raise CommandError('Se requiere manifiesto versión 1 del FabLab indicado.')
        entradas = manifiesto.get('recursos')
        if not isinstance(entradas, list):
            raise CommandError('recursos debe ser una lista.')
        sha = hashlib.sha256(bruto).hexdigest()
        planes, vistos, errores = [], set(), []
        with transaction.atomic():
            consulta = Unidad.objects.filter(slug=SLUG)
            unidad = (consulta.select_for_update() if opciones['aplicar'] else consulta).first()
            if unidad is None:
                raise CommandError('No existe el FabLab solicitado.')
            for indice, entrada in enumerate(entradas, 1):
                try:
                    if not isinstance(entrada, dict) or set(entrada) - CAMPOS_ENTRADA:
                        raise ValidationError('Entrada inválida o con campos no admitidos.')
                    tipo, pk = entrada.get('tipo'), entrada.get('id')
                    if tipo not in TIPOS or not isinstance(pk, int) or isinstance(pk, bool) or pk <= 0:
                        raise ValidationError('tipo/id no válidos.')
                    if (tipo, pk) in vistos:
                        raise ValidationError('El mismo recurso aparece más de una vez.')
                    vistos.add((tipo, pk))
                    consulta = TIPOS[tipo].objects.filter(pk=pk)
                    if tipo == 'equipo':
                        consulta = consulta.filter(Q(unidades__laboratorio=unidad) | Q(unidades__laboratorios=unidad)).distinct()
                    else:
                        consulta = consulta.filter(unidad=unidad)
                    # DISTINCT puede abarcar varias asociaciones; bloquear sólo la fila del recurso.
                    ids = list(consulta.values_list('pk', flat=True))
                    if not ids:
                        raise ValidationError('El recurso no pertenece ni está asociado al FabLab.')
                    consulta = TIPOS[tipo].objects.filter(pk=pk)
                    objeto = (consulta.select_for_update() if opciones['aplicar'] else consulta).get()
                    _validar_identidad(objeto, entrada)
                    planes.append(self._plan(objeto, tipo, entrada))
                except (ValidationError, ValueError, TypeError) as error:
                    detalle = '; '.join(error.messages) if isinstance(error, ValidationError) else str(error)
                    errores.append(f'Entrada {indice}: {detalle}')
            if errores:
                raise CommandError('\n'.join(errores))
            resumen = Counter(recursos_revisados=len(planes))
            informe = {'version': 1, 'unidad': SLUG, 'manifiesto_sha256': sha,
                       'aplicado': opciones['aplicar'], 'recursos': []}
            for plan in planes:
                objeto, cambios, videos = plan['objeto'], plan['cambios'], plan['videos']
                informe['recursos'].append({'tipo': plan['tipo'], 'id': objeto.pk, 'codigo': objeto.codigo,
                    'cambios': cambios, 'videos_nuevos': [{'url': v.url, 'titulo': v.titulo, 'canal': v.canal} for v in videos],
                    'avisos': plan['avisos']})
                if not cambios and not videos:
                    continue
                resumen['recursos_con_cambios'] += 1
                resumen['videos_nuevos'] += len(videos)
                if opciones['aplicar']:
                    anteriores = {campo: deepcopy(getattr(objeto, campo)) for campo in cambios}
                    if cambios:
                        for campo, valor in cambios.items():
                            setattr(objeto, campo, valor)
                        campos = list(cambios)
                        if any(campo.name == 'fecha_actualizacion' for campo in objeto._meta.fields):
                            campos.append('fecha_actualizacion')
                        objeto.save(update_fields=campos)
                    for video in videos:
                        video.save()
                    registrar_auditoria(None, unidad=unidad, accion='actualizar', objeto=objeto,
                        descripcion='Medios de referencia FabLab importados desde manifiesto revisado',
                        anteriores=anteriores,
                        nuevos={'manifiesto_sha256': sha, 'cambios': cambios,
                                'fuentes': plan['fuentes'], 'videos': [v.url for v in videos]})
            informe['resumen'] = dict(resumen)
        if opciones.get('informe'):
            destino = Path(opciones['informe'])
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(('Aplicado' if opciones['aplicar'] else 'Simulación sin guardar') + ': ' +
                          ', '.join(f'{valor} {clave}' for clave, valor in resumen.items()))
        for recurso in informe['recursos']:
            for aviso in recurso['avisos']:
                self.stdout.write(f'{recurso["tipo"]} {recurso["id"]}: {aviso}')

    def _plan(self, objeto, tipo, entrada):
        avisos = []
        actual = deepcopy(objeto.medios_referencia or {})
        if not isinstance(actual, dict):
            raise ValidationError('Los medios actuales no son un objeto; requieren revisión antes de importar.')
        entrante = entrada.get('medios_referencia', {})
        if not isinstance(entrante, dict):
            raise ValidationError('medios_referencia debe ser un objeto.')
        objeto._meta.get_field('medios_referencia').clean(entrante, objeto)
        reemplazar = 'medios_referencia_esperado' in entrada
        if reemplazar and not isinstance(entrada['medios_referencia_esperado'], dict):
            raise ValidationError('medios_referencia_esperado debe ser un objeto.')
        if getattr(objeto, 'logo' if tipo == 'software' else 'imagen'):
            entrante = {k: v for k, v in entrante.items() if k != 'imagen'}
        medios = combinar(actual, entrante, reemplazar)
        cambios, medios = _plan_imagen(objeto, tipo, entrada, medios, avisos)
        if reemplazar and entrada['medios_referencia_esperado'] != actual and medios != actual:
            raise ValidationError('medios_referencia cambió desde la revisión; se conserva.')
        if medios != actual:
            cambios['medios_referencia'] = medios
        informacion = entrada.get('informacion', {})
        if not isinstance(informacion, dict) or set(informacion) - INFORMACION[tipo]:
            raise ValidationError('informacion incluye campos no admitidos.')
        if tipo == 'equipo' and objeto.origen_datos_tecnicos == 'medido':
            if informacion:
                avisos.append('Levantamiento medido protegido; no se cambia información técnica.')
        else:
            for campo, valor in informacion.items():
                previo = getattr(objeto, campo)
                if campo == 'especificaciones':
                    if not isinstance(valor, dict):
                        raise ValidationError('especificaciones debe ser un objeto.')
                    combinado = combinar(previo or {}, valor)
                    if combinado != (previo or {}):
                        cambios[campo] = combinado
                elif vacio(previo) and not vacio(valor):
                    cambios[campo] = valor
        videos = entrada.get('videos', [])
        if not isinstance(videos, list):
            raise ValidationError('videos debe ser una lista.')
        if tipo != 'equipo' and videos:
            raise ValidationError('Videos de software/consumibles deben ir en medios_referencia.videos.')
        nuevos = _videos_nuevos(objeto, videos) if tipo == 'equipo' else []
        # Validar los campos modificados, sin revalidar stock, estados ni datos legados que no se modifican.
        for campo, valor in cambios.items():
            cambios[campo] = objeto._meta.get_field(campo).clean(valor, objeto)
        return {'objeto': objeto, 'tipo': tipo, 'cambios': cambios, 'videos': nuevos,
                'avisos': avisos, 'fuentes': {'imagen': entrada.get('imagen'), 'medios_referencia': entrante}}
