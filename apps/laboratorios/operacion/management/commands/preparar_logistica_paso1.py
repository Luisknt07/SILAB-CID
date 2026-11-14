"""Publica el paquete metodológico LOG-P1 sin alterar la operación del laboratorio.

--simular sólo lee: no usa transacciones, secuencias, SELECT FOR UPDATE ni archivos.
--aplicar bloquea la unidad, respalda registros y conserva cambios editoriales.
Los adjuntos propios se generan localmente; nunca se descargan archivos externos.
"""
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_LABORATORIO
from apps.gestion_unidades.management.fichas_area import FUENTES_DE_CARGADOR
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import AREAS_PASO1, FACULTAD_UPEC, FICHA_CAMPOS, FUENTES, GUIAS, LEGADO_FICHAS_SHA256, MATRIZ_ASIGNATURAS, SLUG, VERSION, documento_html, valores_ficha
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.directorio_unidades.models.core import Unidad

MARCA = 'Contenido docente original UPEC | LOG-P1:v1 | sha256:'
RECURSO_MARCA = re.compile(r'^log-p1:([a-z0-9-]+);sha256:([a-f0-9]{64})$')
RECURSO_CAMPOS = (
    'nombre', 'descripcion', 'url', 'activo', 'visibilidad', 'descargar', 'carpeta_id',
    'tipo_adjunto', 'autor', 'fuente', 'licencia_uso', 'version', 'estado',
    'seguridad_verificada', 'navegador_remoto', 'hash_sha256',
)
SECCION_FUENTES = {
    'mit-beer': '4.4', 'scor': '3.2', 'gs1-traza': '3.2', 'gs1-epcis': '4.4',
    'rutas': '4.4', 'simpy': '2.3', 'senae': '3.2', 'icc': '3.2',
    'seguridad': '1.4', 'ia': '4.4', 'series': '4.4', 'upec': '4.2',
}


def huella(valores):
    contenido = json.dumps(valores, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()


def huella_ficha(ficha):
    return huella({campo: getattr(ficha, campo) for campo in FICHA_CAMPOS})


def huella_recurso(recurso):
    valores = {campo: getattr(recurso, campo) for campo in RECURSO_CAMPOS}
    valores['archivo'] = recurso.archivo.name or ''
    return huella(valores)


def guia_area(codigo, area):
    return {
        'titulo': 'Ficha metodológica: ' + area['titulo'], 'seccion': '2.1',
        'carpeta': 'Capacidades y configuración verificables', 'fuentes': area['fuentes'],
        'objetivo': area['que_es'],
        'bloques': [
            ('Cómo se trabaja', [area['como_funciona']]),
            ('Secuencia y controles', [titulo + ': ' + texto for titulo, texto in area['principio']]),
            ('Prácticas y competencias', area['aplicaciones'] + area['competencias']),
            ('Indicadores', area['indicadores']),
            ('Infraestructura y seguridad', area['conexiones'] + area['seguridad']),
            ('Alcance presencial', [
                'La publicación de esta ficha valida su contenido metodológico, no verifica la existencia o estado de equipos.',
                'Consultar inventario, manuales y responsable antes de usar una maqueta; los elementos sugeridos son referencias.',
                'Código de área: ' + codigo + '. Se conservan sus vínculos con equipos, reservas y asignaturas.',
            ]),
        ],
    }


def guia_academica(asignaturas):
    bloques = [('Alcance', [
        'La matriz complementa las asignaturas y carreras ya registradas en la unidad; no sustituye la malla ni el sílabo aprobado.',
        'Se conserva código, nombre, semestre, docente y estado de cada asignatura. Las actividades son orientaciones docentes.',
        'Tecnologías aplicadas y simulación logística aporta captura, programación y análisis de forma transversal.',
    ])]
    for asignatura in asignaturas:
        fila = MATRIZ_ASIGNATURAS.get(asignatura.codigo)
        if not fila:
            continue
        nombres = [AREAS_PASO1[codigo]['titulo'] for codigo in fila['areas']]
        bloques.append((asignatura.nombre + ' — ' + (asignatura.carrera or 'Carrera registrada en la unidad'), [
            'Código registrado: ' + asignatura.codigo + '. Nivel registrado: ' + (asignatura.semestre or 'Consultar planificación académica') + '.',
            'Áreas de práctica propuestas: ' + '; '.join(nombres) + '.',
            'Resultado observable: ' + fila['resultado'], 'Evidencia: ' + fila['evidencia'],
            'El docente adapta complejidad, duración y evaluación al sílabo y recursos autorizados.',
        ]))
    return {
        'titulo': 'Matriz académica: asignaturas, áreas, prácticas y evidencias', 'seccion': '4.2',
        'carpeta': 'Ruta académica y evaluación aplicada', 'fuentes': ('upec', 'scor'),
        'objetivo': 'Conectar cada asignatura existente con decisiones, prácticas y evidencia útil de aprendizaje.',
        'bloques': bloques,
    }


def recursos_del_paquete(asignaturas):
    guias = dict(GUIAS)
    guias['matriz-academica'] = guia_academica(asignaturas)
    guias.update({'area-' + codigo.lower(): guia_area(codigo, area) for codigo, area in AREAS_PASO1.items()})
    resultado = []
    for clave, guia in guias.items():
        resultado.append({
            'clave': clave, 'nombre': guia['titulo'], 'seccion': guia['seccion'], 'carpeta': guia['carpeta'],
            'descripcion': guia['objetivo'], 'tipo_adjunto': 'manual', 'fuente': 'interna',
            'licencia_uso': 'interna', 'autor': 'UPEC · Contenido metodológico de logística',
            'url': '', 'html': documento_html(clave, guia),
        })
    for clave, fuente in FUENTES.items():
        resultado.append({
            'clave': 'fuente-' + clave, 'nombre': fuente['entidad'] + ' — ' + fuente['titulo'],
            'seccion': SECCION_FUENTES[clave], 'carpeta': 'Fuentes primarias de ' + MAPA_LABORATORIO.secciones[SECCION_FUENTES[clave]]['titulo'],
            'descripcion': fuente['uso'] + ' ' + fuente['limitacion'] + ' Consulta: ' + fuente['consulta'] + '.',
            'tipo_adjunto': 'publicacion', 'fuente': 'externa', 'licencia_uso': 'restringida',
            'autor': fuente['entidad'], 'url': fuente['url'], 'html': '',
        })
    return resultado


def contenido_recurso(datos):
    """Bytes deterministas de un documento o dataset original del paquete."""
    if 'contenido' in datos:
        return datos['contenido']
    return datos['html'].encode('utf-8') if datos['html'] else b''


def nombre_archivo_recurso(datos):
    return datos.get('nombre_archivo', 'log-p1-' + datos['clave'] + '.html')


class Command(BaseCommand):
    help = 'Completa seis fichas y publica guías de logística con respaldo, versiones y preservación editorial.'
    descripcion_auditoria = 'LOG-P1: seis áreas y contenidos metodológicos de logística; sin cambio de inventario ni oferta'
    prefijo_respaldo = 'logistica-paso1-'

    def add_arguments(self, parser):
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument('--simular', action='store_true', help='Sólo SELECT; no crea registros ni archivos.')
        modo.add_argument('--aplicar', action='store_true', help='Aplica el paquete revisado con respaldo previo.')
        parser.add_argument('--manifiesto-revision', type=Path, help='Registro de revisión de los hashes HTML y enlaces del paquete.')

    def handle(self, *args, **opciones):
        aplicar = opciones['aplicar']
        self.manifiesto_revision = opciones.get('manifiesto_revision')
        archivos_nuevos = []
        self.directorios_nuevos = []
        if not aplicar:
            unidad = self._unidad()
            resumen, avisos, _ = self._preparar(unidad, aplicar=False, archivos_nuevos=archivos_nuevos)
        else:
            try:
                with transaction.atomic():
                    unidad = self._unidad(bloquear=True)
                    resumen, avisos, objetos = self._preparar(
                        unidad, aplicar=False, archivos_nuevos=archivos_nuevos, bloquear=True)
                    if any(valor for clave, valor in resumen.items() if clave != 'preservados'):
                        self._validar_revision(list(unidad.asignaturas.all()))
                        respaldo = self._respaldar(objetos)
                        self.stdout.write('Respaldo previo: ' + str(respaldo))
                        resumen, avisos, _ = self._preparar(unidad, aplicar=True, archivos_nuevos=archivos_nuevos)
                        registrar_auditoria(
                            unidad=unidad, accion='actualizar', objeto=unidad,
                            descripcion=self.descripcion_auditoria,
                            nuevos=dict(resumen),
                        )
            except Exception:
                # Sólo archivos creados por esta ejecución, nunca archivos previos.
                for storage, nombre in archivos_nuevos:
                    storage.delete(nombre)
                raiz = (Path(settings.MEDIA_ROOT) / 'recursos' / 'archivos').resolve()
                for directorio in reversed(self.directorios_nuevos):
                    # Sólo extracciones de esta ejecución y dentro de media/recursos/archivos.
                    if directorio.parent == raiz and directorio.is_dir() and not directorio.is_symlink():
                        shutil.rmtree(directorio)
                raise
        for aviso in avisos:
            self.stdout.write(self.style.WARNING(aviso))
        detalle = ', '.join(f'{cantidad} {nombre}' for nombre, cantidad in resumen.items() if cantidad) or 'sin cambios'
        prefijo = '' if aplicar else '[simulación SELECT] '
        self.stdout.write(self.style.SUCCESS(prefijo + detalle + '.'))

    def _recursos(self, asignaturas):
        return recursos_del_paquete(asignaturas)

    def _validar_revision(self, asignaturas):
        if self.manifiesto_revision is None:
            raise CommandError('Para aplicar, indique --manifiesto-revision tras revisar los archivos exactos y enlaces.')
        try:
            manifiesto = json.loads(self.manifiesto_revision.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise CommandError('No se puede leer el manifiesto de revisión.') from exc
        esperados = {hashlib.sha256(contenido_recurso(datos)).hexdigest()
                     for datos in self._recursos(asignaturas) if contenido_recurso(datos)}
        if not isinstance(manifiesto, dict):
            raise CommandError('El manifiesto de revisión debe ser un objeto JSON.')
        revisados = manifiesto.get('sha256', [])
        if (not isinstance(revisados, list) or not all(isinstance(fila, str) for fila in revisados)
                or not esperados.issubset(set(revisados))
                or manifiesto.get('resultado') != 'sin_amenazas'
                or not isinstance(manifiesto.get('motor'), str) or not manifiesto['motor'].strip()
                or not isinstance(manifiesto.get('fecha'), str) or not manifiesto['fecha'].strip()
                or manifiesto.get('fuentes_enlaces_revisadas') is not True):
            raise CommandError('La revisión no cubre los hashes exactos, el resultado de seguridad y los enlaces del paquete.')

    @staticmethod
    def _unidad(bloquear=False):
        consulta = Unidad.objects.select_for_update() if bloquear else Unidad.objects.all()
        unidad = consulta.filter(slug=SLUG).first()
        if unidad is None:
            raise CommandError('No existe el laboratorio de Logística; no se crea otra unidad.')
        if unidad.codigo_base != 'laboratorios':
            raise CommandError('La unidad debe conservar su tipo laboratorio.')
        return unidad

    def _respaldar(self, objetos):
        carpeta = Path(settings.BASE_DIR) / 'var' / 'backups'
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / (self.prefijo_respaldo + timezone.now().strftime('%Y%m%dT%H%M%S%f') + '.json')
        destino.write_text(serializers.serialize('json', objetos, ensure_ascii=False, indent=2), encoding='utf-8')
        return destino

    def _preparar(self, unidad, *, aplicar, archivos_nuevos, bloquear=False):
        resumen, avisos = Counter(), []
        def consulta(filas):
            return filas.select_for_update() if bloquear or aplicar else filas
        areas = {area.codigo: area for area in consulta(unidad.espacios_reservables.all())}
        faltan = set(AREAS_PASO1) - areas.keys()
        if faltan:
            raise CommandError('Faltan áreas existentes: ' + ', '.join(sorted(faltan)))
        if any(areas[codigo].integrada_en_id for codigo in AREAS_PASO1):
            raise CommandError('Una de las seis áreas está integrada en otra; revisar antes de publicar.')
        modulos = {modulo.clave: modulo for modulo in consulta(unidad.modulos_contenido.all())}
        faltan_modulos = set(MAPA_LABORATORIO.pestanas) - modulos.keys()
        if faltan_modulos:
            raise CommandError('Faltan pestañas existentes: ' + ', '.join(sorted(faltan_modulos)))
        fichas = {ficha.espacio_id: ficha for ficha in consulta(FichaArea.objects.filter(espacio__unidad=unidad))}
        elementos = list(consulta(ElementoFichaArea.objects.filter(ficha__espacio__unidad=unidad)))
        carpetas = list(consulta(unidad.carpetas.all()))
        recursos = list(consulta(unidad.recursos.all()))
        asignaturas = list(consulta(unidad.asignaturas.all()))
        objetos = [unidad, *areas.values(), *modulos.values(), *fichas.values(), *elementos, *carpetas, *recursos, *asignaturas]
        investigacion = modulos['investigacion-formativa']
        paquete_previo = any((recurso.palabras_clave or '').startswith('log-p1:') for recurso in recursos)
        if not investigacion.activo and not paquete_previo:
            resumen['pestañas activadas'] += 1
            if aplicar:
                investigacion.activo = True
                investigacion.save(update_fields=['activo'])
        elif not investigacion.activo:
            avisos.append('Investigación formativa: se conserva la desactivación posterior del módulo.')
        if not unidad.facultad.strip():
            resumen['facultad completada'] += 1
            if aplicar:
                unidad.facultad = FACULTAD_UPEC
                unidad.save(update_fields=['facultad'])
        for codigo, area in AREAS_PASO1.items():
            espacio, ficha = areas[codigo], fichas.get(areas[codigo].pk)
            valores = valores_ficha(area)
            if ficha is None:
                resumen['fichas publicadas'] += 1
                if aplicar:
                    ficha = FichaArea.objects.create(espacio=espacio, fuente=MARCA + huella(valores), **valores)
                    fichas[espacio.pk] = ficha
            else:
                actual = huella_ficha(ficha)
                propia = ficha.fuente == MARCA + actual
                legado = (not ficha.publicada and ficha.fuente in FUENTES_DE_CARGADOR
                          and actual == LEGADO_FICHAS_SHA256.get(codigo))
                if propia or legado:
                    fuente = MARCA + huella(valores)
                    if any(getattr(ficha, campo) != valor for campo, valor in valores.items()) or ficha.fuente != fuente:
                        resumen['fichas publicadas'] += 1
                        if aplicar:
                            for campo, valor in valores.items():
                                setattr(ficha, campo, valor)
                            ficha.fuente = fuente
                            ficha.save(update_fields=[*valores, 'fuente', 'actualizado_en'])
                else:
                    resumen['preservados'] += 1
                    avisos.append(codigo + ': se conserva la ficha editada por la unidad; el contenido nuevo está en su guía metodológica.')
            if aplicar and ficha:
                urls = {elemento.url for elemento in elementos if elemento.ficha_id == ficha.pk}
                for orden, clave in enumerate(area['fuentes'], start=1):
                    fuente = FUENTES[clave]
                    if fuente['url'] not in urls:
                        ElementoFichaArea.objects.create(
                            ficha=ficha, tipo='documento', nombre=fuente['entidad'] + ' — ' + fuente['titulo'],
                            url=fuente['url'], para_que=fuente['uso'], orden=100 + orden,
                        )
                        urls.add(fuente['url'])
                        resumen['referencias de área'] += 1
            elif not aplicar:
                urls = {elemento.url for elemento in elementos if ficha and elemento.ficha_id == ficha.pk}
                resumen['referencias de área'] += sum(FUENTES[clave]['url'] not in urls for clave in area['fuentes'])
        gestionados = {}
        for recurso in recursos:
            marca = RECURSO_MARCA.fullmatch(recurso.palabras_clave or '')
            identidad = re.match(r'^log-p1:([a-z0-9-]+)(?:;|$)', recurso.palabras_clave or '')
            if identidad:
                if identidad[1] in gestionados:
                    raise CommandError('Identificador LOG-P1 duplicado: ' + identidad[1])
                gestionados[identidad[1]] = (recurso, marca[2] if marca else '')
        carpetas_resueltas = {}
        for datos in self._recursos(asignaturas):
            clave = datos['clave']
            recurso, anterior = gestionados.get(clave, (None, ''))
            if recurso is None:
                recurso = next((fila for fila in recursos if fila.nombre_original == nombre_archivo_recurso(datos)
                                or (fila.nombre == datos['nombre'] and (not datos['url'] or fila.url == datos['url']))), None)
            if recurso and anterior != huella_recurso(recurso):
                resumen['preservados'] += 1
                avisos.append(clave + ': se conserva el recurso editado o desactivado manualmente.')
                continue
            carpeta_clave = (datos['seccion'], datos['carpeta'])
            if carpeta_clave not in carpetas_resueltas:
                # Conservar renombre/orden manual de la carpeta que ya contiene un recurso propio.
                misma = next((r.carpeta for r, _ in gestionados.values()
                              if r.carpeta_id and r.carpeta.seccion_planta == datos['seccion']
                              and r.carpeta.nombre == datos['carpeta']), None)
                carpeta = recurso.carpeta if recurso and recurso.carpeta_id else misma
                carpeta = carpeta or next((c for c in carpetas if c.nombre == datos['carpeta']), None)
                if carpeta and (carpeta.del_expediente or carpeta.ficha_id or carpeta.carpeta_padre_id
                                or carpeta.seccion_planta != datos['seccion']):
                    raise CommandError('La carpeta «' + datos['carpeta'] + '» tiene otro uso; se conserva sin mezclarla.')
                if carpeta is None:
                    resumen['carpetas creadas'] += 1
                    carpeta = CarpetaRecurso(
                        unidad=unidad, nombre=datos['carpeta'], modulo='recursos',
                        modulo_config=modulos[MAPA_LABORATORIO.modulo_de(datos['seccion'])],
                        seccion_planta=datos['seccion'], orden=50, activa=True, visibilidad='publica',
                    )
                    if aplicar:
                        carpeta.full_clean()
                        carpeta.save()
                carpetas_resueltas[carpeta_clave] = carpeta
            carpeta = carpetas_resueltas[carpeta_clave]
            contenido = contenido_recurso(datos)
            esperado_hash = hashlib.sha256(contenido).hexdigest() if contenido else ''
            valores = {
                campo: datos[campo] for campo in ('nombre', 'descripcion', 'url', 'tipo_adjunto', 'autor', 'fuente', 'licencia_uso')
            }
            valores.update({
                'activo': True, 'visibilidad': 'publica', 'descargar': bool(contenido),
                'carpeta_id': carpeta.pk, 'version': VERSION, 'estado': 'vigente',
                'seguridad_verificada': True, 'navegador_remoto': False,
            })
            cambia = (recurso is None or any(getattr(recurso, campo) != valor for campo, valor in valores.items())
                      or recurso.hash_sha256 != esperado_hash)
            if not cambia:
                continue
            resumen['recursos publicados'] += 1
            if not aplicar:
                continue
            recurso = recurso or Recurso(unidad=unidad)
            for campo, valor in valores.items():
                setattr(recurso, campo, valor)
            try:
                if contenido and recurso.hash_sha256 != esperado_hash:
                    recurso.archivo.save(nombre_archivo_recurso(datos), ContentFile(contenido), save=False)
                    archivos_nuevos.append((recurso.archivo.storage, recurso.archivo.name))
                    if recurso.es_zip:
                        directorio = recurso.directorio_extraido.resolve()
                        raiz = (Path(settings.MEDIA_ROOT) / 'recursos' / 'archivos').resolve()
                        if directorio.parent != raiz or directorio.exists():
                            raise CommandError('La extracción del nuevo ZIP coincide con un directorio previo; se conserva sin modificarlo.')
                        self.directorios_nuevos.append(directorio)
                recurso.full_clean()
                recurso.save()
                recurso.palabras_clave = 'log-p1:' + clave + ';sha256:' + huella_recurso(recurso)
                recurso.save(update_fields=['palabras_clave'])
            finally:
                # clean/save calculan la huella y pueden abrir el FieldFile desde storage.
                # Cerrar antes del commit o rollback evita bloqueos de archivo en Windows.
                recurso.archivo.close()
        # Corrección acotada y verificada por nombre original + huella del archivo.
        for recurso in recursos:
            if (recurso.nombre_original == 'SOLICITUD_DE_COMPRA_11983_2026.pdf'
                    and recurso.hash_sha256 == '334909dfb31c4da9660353a94ee34624eecb0468fae6d333d6ca00a249f6da7e'
                    and recurso.nombre == 'Guia de laboratorio' and recurso.visibilidad == 'publica'
                    and not (recurso.carpeta_id and recurso.carpeta.del_expediente)):
                resumen['archivos reclasificados'] += 1
                if aplicar:
                    recurso.nombre = 'Solicitud de compra 11983/2026 — documento interno'
                    recurso.descripcion = ('Documento administrativo identificado por sus metadatos originales; '
                                           'no corresponde a una guía de práctica. Acceso restringido al personal de la unidad.')
                    recurso.visibilidad = 'interna'
                    # Sólo metadatos: no abre ni reescribe el documento administrativo.
                    Recurso.objects.filter(pk=recurso.pk).update(
                        nombre=recurso.nombre, descripcion=recurso.descripcion, visibilidad=recurso.visibilidad)
        # Enlace legado revisado contra su página original: ABE trata biotecnología,
        # no realidad virtual logística. Se conserva el enlace para revisión interna.
        for recurso in recursos:
            if (recurso.nombre == 'Virtual reality' and recurso.descripcion == 'virtual'
                    and recurso.url == 'https://www.labxchange.org/library/clusters/lx-cluster:abe'
                    and not recurso.archivo and recurso.visibilidad == 'publica'
                    and not (recurso.carpeta_id and recurso.carpeta.del_expediente)):
                resumen['enlaces reclasificados'] += 1
                if aplicar:
                    Recurso.objects.filter(pk=recurso.pk).update(
                        nombre='LabXchange ABE — fundamentos de biotecnología',
                        descripcion=('Referencia externa de LabXchange ABE sobre conceptos y técnicas de biotecnología. '
                                     'No corresponde a realidad virtual logística; se conserva internamente para revisar '
                                     'su pertinencia antes de incluirla en una ruta de aprendizaje del laboratorio.'),
                        fuente='externa', visibilidad='interna',
                    )
        return resumen, avisos, objetos
