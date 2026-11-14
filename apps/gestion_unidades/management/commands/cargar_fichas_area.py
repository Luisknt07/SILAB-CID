"""Carga las fichas explicativas de las áreas de todas las unidades, sin publicarlas.

Cada ficha trae qué es y cómo funciona el área, su diagrama paso a paso, el boceto de su
distribución, sus aplicaciones, el equipamiento con ficha técnica (y el enlace al equipo ya
registrado cuando existe), los insumos y materiales, el software, la documentación, las
conexiones, la seguridad, y sus imágenes y videos. El contenido está en
`apps/gestion_unidades/management/fichas_area/`.

Es idempotente: una ficha que ya existe se conserva. Con `--reemplazar-borradores` se
rehacen las que siguen sin publicar y salieron de un cargador (su fuente lo dice); las
publicadas o escritas por la unidad nunca se tocan. Con `--medios`, las fichas que ya existen
y no tienen imágenes ni videos los reciben, sin tocar su texto. `--simular` no guarda nada.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.management.fichas_area import FICHAS, FUENTE, FUENTES_DE_CARGADOR
from apps.gestion_unidades.management.fichas_area.medios import imagenes_de, videos_de
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class Simulacion(Exception):
    """Deshace la carga al final de una simulación."""


class Command(BaseCommand):
    help = 'Carga sin publicar las fichas explicativas de las áreas de todas las unidades.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', action='append', choices=sorted(FICHAS), help='Solo esta unidad; se puede repetir.')
        parser.add_argument('--reemplazar-borradores', action='store_true',
                            help='Rehace las fichas sin publicar que salieron de un cargador.')
        parser.add_argument('--medios', action='store_true',
                            help='Suma imágenes y videos a las fichas que ya existen y no los tienen.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        total = Counter()
        for slug in opciones['unidad'] or FICHAS:
            unidad = Unidad.objects.filter(slug=slug).first()
            if unidad is None:
                self.stdout.write(self.style.WARNING(f'{slug}: no existe; se omite.'))
                continue
            try:
                with transaction.atomic():
                    resumen, avisos = self._cargar(unidad, FICHAS[slug], opciones['reemplazar_borradores'],
                                                   opciones['medios'])
                    if opciones['simular']:
                        raise Simulacion
                    if resumen['fichas'] or resumen['medios']:
                        registrar_auditoria(None, unidad=unidad, accion='actualizar', objeto=unidad,
                                            descripcion='Carga sin publicar de las fichas de sus áreas',
                                            nuevos=dict(resumen))
            except Simulacion:
                pass
            total.update(resumen)
            prefijo = '[simulación] ' if opciones['simular'] else ''
            detalle = ', '.join(f'{cantidad} {nombre}' for nombre, cantidad in resumen.items() if cantidad) or 'nada nuevo'
            self.stdout.write(self.style.SUCCESS(f'{prefijo}{unidad.nombre}: {detalle}.'))
            for aviso in avisos:
                self.stdout.write(f'  aviso: {aviso}')
        self.stdout.write(f'Total: {total["fichas"]} fichas, {total["equipos"]} equipos, {total["insumos"]} insumos, '
                          f'{total["imagenes"]} imágenes y {total["videos"]} videos.')

    def _cargar(self, unidad, fichas, reemplazar, medios):
        resumen, avisos = Counter(), []
        areas = {area.codigo: area for area in EspacioReservable.objects.filter(unidad=unidad)}
        equipos = {equipo.codigo_unidad: equipo for equipo in UnidadEquipo.objects.filter(laboratorio=unidad)}
        for codigo, datos in fichas.items():
            espacio = areas.get(codigo)
            if espacio is None:
                avisos.append(f'el área {codigo} no existe; su ficha no se carga.')
                continue
            if espacio.integrada_en_id:
                # Su ficha ya se unió a la del área que la integró: cargarla de nuevo duplicaría los equipos.
                continue
            existente = FichaArea.objects.filter(espacio=espacio).first()
            if existente:
                if not (reemplazar and not existente.publicada and existente.fuente in FUENTES_DE_CARGADOR):
                    tiene = set(existente.elementos.filter(tipo__in=('imagen', 'video')).values_list('tipo', flat=True))
                    if medios and len(tiene) < 2 and self._medios(existente, unidad.slug, codigo, resumen, ya_tiene=tiene):
                        resumen['medios'] += 1
                    continue
                existente.delete()
            ficha = self._ficha(espacio, datos, equipos, avisos, resumen)
            self._medios(ficha, unidad.slug, codigo, resumen)
        return resumen, avisos

    @staticmethod
    def _ficha(espacio, datos, equipos, avisos, resumen):
        ficha = FichaArea.objects.create(
            espacio=espacio, que_es=datos['que_es'], como_funciona=datos['como_funciona'],
            principio='\n'.join(f'{titulo} | {explicacion}' for titulo, explicacion in datos['principio']),
            distribucion='\n'.join(f'{zona} | {uso} | {"; ".join(nombres)}' for zona, uso, nombres in datos['distribucion']),
            aplicaciones='\n'.join(datos['aplicaciones']), conexiones='\n'.join(datos['conexiones']),
            seguridad='\n'.join(datos['seguridad']), fuente=FUENTE, publicada=False,
        )
        elementos = []
        for orden, equipo in enumerate(datos['equipos'], start=1):
            registrado = equipos.get(equipo['registrado']) if equipo['registrado'] else None
            if equipo['registrado'] and registrado is None:
                avisos.append(f'{espacio.codigo}: el equipo {equipo["registrado"]} no está registrado; queda como referencia.')
            elementos.append(ElementoFichaArea(
                ficha=ficha, tipo='equipo', nivel=equipo['nivel'], nombre=equipo['nombre'], icono=equipo['icono'],
                para_que=equipo['para_que'], ejemplo=equipo['ejemplo'], cantidad=equipo['cantidad'],
                especificaciones='\n'.join(f'{clave}: {valor}' for clave, valor in equipo['especificaciones']),
                consumibles='\n'.join(equipo['insumos']), cuidados='\n'.join(equipo['cuidados']),
                registrado=registrado, solo_referencia=equipo.get('solo_referencia', False), orden=orden,
            ))
        elementos += [
            ElementoFichaArea(ficha=ficha, tipo='insumo', nombre=nombre, para_que=para_que, cantidad=consumo,
                              ejemplo=presentacion, orden=orden)
            for orden, (nombre, para_que, consumo, presentacion) in enumerate(datos['insumos'], start=1)
        ] + [
            ElementoFichaArea(ficha=ficha, tipo='software', nombre=nombre, licencia=licencia, para_que=para_que,
                              url=url, orden=orden)
            for orden, (nombre, licencia, para_que, url) in enumerate(datos['software'], start=1)
        ] + [
            ElementoFichaArea(ficha=ficha, tipo='documento', nombre=nombre, url=url, para_que=para_que, orden=orden)
            for orden, (nombre, url, para_que) in enumerate(datos['documentacion'], start=1)
        ]
        ElementoFichaArea.objects.bulk_create(elementos)
        resumen['fichas'] += 1
        resumen['equipos'] += len(datos['equipos'])
        resumen['insumos'] += len(datos['insumos'])
        return ficha

    @staticmethod
    def _medios(ficha, slug, codigo, resumen, ya_tiene=()):
        """El collage referencial del área y sus videos verificados; lo que la ficha ya tiene no se repite."""
        imagenes = [] if 'imagen' in ya_tiene else imagenes_de(slug, codigo)
        videos = [] if 'video' in ya_tiene else videos_de(slug, codigo)
        ElementoFichaArea.objects.bulk_create([
            ElementoFichaArea(ficha=ficha, tipo='imagen', nombre=pie, imagen_estatica=ruta, orden=orden)
            for orden, (ruta, pie) in enumerate(imagenes, start=1)
        ] + [
            ElementoFichaArea(ficha=ficha, tipo='video', nombre=titulo, ejemplo=canal, para_que=descripcion,
                              url=f'https://www.youtube.com/watch?v={identificador}', orden=orden)
            for orden, (identificador, titulo, canal, descripcion) in enumerate(videos, start=1)
        ])
        resumen['imagenes'] += len(imagenes)
        resumen['videos'] += len(videos)
        return len(imagenes) + len(videos)
