"""Importa el «Reporte de bienes» de la bodega de la Universidad (CSV) al inventario de una unidad.

El archivo es el que entrega bodega, guardado como CSV (separado por punto y coma o coma), con las
columnas Código del bien, BLD/BCA, Serie/Identificación (la descripción), Modelo, Marca, Color,
Material, Dimensiones, Ubicación de bodega, Custodio, Fecha de ingreso y Valor contable.

Cada bien se busca, en este orden, por su código, por su número de serie y, dentro de la unidad, entre
los equipos que aún no tienen código cuyo nombre o modelo de referencia coincide con la descripción,
la marca y el modelo del bien: así el código oficial reemplaza a la unidad de referencia en lugar de
duplicarla. Solo si nada coincide se registra un equipo nuevo. Lo que la unidad ya cargó no se pisa
(solo se llenan los campos vacíos) y cada cambio queda en la historia del equipo. --simular muestra lo
que haría, fila por fila, sin guardar nada.

También recibe una carpeta con un CSV por área, cada uno nombrado con el código del área
(FAB-AREA-IMP3D.csv…): así se guardan, ya conciliados, los reportes de
apps/recursos/management/bienes_bodega/.
"""
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.presentation.codigos_equipo import limpiar_codigo_bien
from apps.recursos.presentation.catalogo_inventario import asignar_familia, palabras, se_excluyen, semejanza
from apps.core.presentation.codigos_sistema import siguiente_codigo_modelo, siguiente_codigo_unidad
from apps.recursos.presentation.reportes_bodega import fecha_de, leer, serie_de, valor_de
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

class Simulacion(Exception):
    """Deshace la importación al final de una simulación."""


class Command(BaseCommand):
    help = 'Importa el reporte de bienes de bodega (CSV): asigna los códigos oficiales y completa el registro patrimonial.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='CSV del reporte de bienes, o carpeta con un CSV por código de área.')
        parser.add_argument('--unidad', required=True, help='Slug de la unidad que custodia los bienes.')
        parser.add_argument('--area', help='Código del área donde se ubican los equipos nuevos.')
        parser.add_argument('--enlazar-por-nombre', action='store_true',
                            help='Asigna el código al equipo sin código que mejor coincide por nombre (revisa antes la simulación).')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        unidad = Unidad.objects.filter(slug=opciones['unidad']).first()
        if unidad is None:
            raise CommandError(f'No existe la unidad {opciones["unidad"]}.')
        ruta = Path(opciones['archivo'])
        if ruta.is_dir():
            if opciones['area']:
                raise CommandError('Con una carpeta, el área sale del nombre de cada archivo: no uses --area.')
            lotes = [(self._area(unidad, archivo.stem), archivo) for archivo in sorted(ruta.glob('*.csv'))]
            if not lotes:
                raise CommandError('La carpeta no tiene archivos CSV.')
        else:
            lotes = [(self._area(unidad, opciones['area']) if opciones['area'] else None, ruta)]
        try:
            bienes = [(area, bien) for area, archivo in lotes for bien in leer(archivo)]
        except ValueError as error:
            raise CommandError(str(error)) from error
        repetidos = [codigo for codigo, veces in Counter(limpiar_codigo_bien(b['codigo_bien']) for _, b in bienes).items()
                     if veces > 1]
        if repetidos:
            raise CommandError(f'El archivo repite códigos de bien: {", ".join(repetidos)}.')
        resumen = Counter()
        try:
            with transaction.atomic():
                for area, bien in bienes:
                    accion, equipo = self._importar(unidad, area, bien, opciones['enlazar_por_nombre'])
                    resumen[accion] += 1
                    self.stdout.write(f'  {limpiar_codigo_bien(bien["codigo_bien"]):>10}  {bien["descripcion"][:42]:42}  '
                                      f'{accion:>22}  {equipo.codigo_unidad} · {equipo.equipo.nombre[:40]}')
                if opciones['simular']:
                    raise Simulacion
                registrar_auditoria(None, unidad=unidad, accion='actualizar', objeto=unidad,
                                    descripcion='Importación del reporte de bienes de bodega', nuevos=dict(resumen))
        except Simulacion:
            pass
        prefijo = '[simulación] ' if opciones['simular'] else ''
        self.stdout.write(self.style.SUCCESS(prefijo + ', '.join(f'{v} {k}' for k, v in sorted(resumen.items()))))

    def _area(self, unidad, codigo):
        area = EspacioReservable.objects.filter(unidad=unidad, codigo=codigo, activo=True).first()
        if area is None:
            raise CommandError(f'La unidad no tiene el área activa {codigo}.')
        return area

    def _importar(self, unidad, area, bien, enlazar_por_nombre):
        codigo = limpiar_codigo_bien(bien['codigo_bien'])
        serie = serie_de(bien)
        de_la_unidad = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct()
        ajeno = UnidadEquipo.objects.filter(codigo_bien=codigo).exclude(pk__in=de_la_unidad.values('pk')).first()
        if ajeno is not None:
            # El bien ya figura en otra unidad: es una transferencia que se hace a mano, no una actualización.
            return 'en otra unidad, sin cambios', ajeno
        equipo = de_la_unidad.filter(codigo_bien=codigo).first()
        accion = 'actualizado'
        if equipo is None and bien.get('codigo_sistema', '').lower() == 'nuevo':
            # Conciliación a mano: es un equipo distinto de todo lo registrado.
            equipo, accion = self._nuevo(unidad, area, bien, codigo, forzar=True), 'registrado nuevo'
        if equipo is None and bien.get('codigo_sistema'):
            equipo = UnidadEquipo.objects.filter(
                Q(laboratorio=unidad) | Q(laboratorios=unidad), codigo_unidad=bien['codigo_sistema'],
                codigo_bien__isnull=True).distinct().first()
            if equipo is None:
                raise CommandError(f'{codigo}: el equipo {bien["codigo_sistema"]} no existe en la unidad o ya tiene código.')
            accion = 'enlazado a mano'
        if equipo is None and serie:
            equipo = de_la_unidad.filter(numero_serie__iexact=serie, codigo_bien__isnull=True).first()
            accion = 'enlazado por serie'
        if equipo is None:
            parecido = self._parecido(unidad, area, bien)
            if parecido is not None and enlazar_por_nombre:
                equipo, accion = parecido, 'enlazado por nombre'
            elif parecido is not None:
                # Sin confirmación no se enlaza: la propuesta se muestra y el bien queda sin tocar.
                return 'propuesto, sin enlazar', parecido
        if equipo is None:
            equipo = self._nuevo(unidad, area, bien, codigo)
            accion = 'registrado nuevo'
        cambios = {
            'codigo_bien': codigo, 'tipo_bien': bien.get('tipo_bien', '').upper()[:3] if bien.get('tipo_bien', '').upper()[:3] in ('BLD', 'BCA') else '',
            'numero_serie': serie, 'custodio': bien.get('custodio', ''), 'ubicacion_bodega': bien.get('ubicacion_bodega', ''),
            'color': bien.get('color', ''), 'material': bien.get('material', ''), 'dimensiones': bien.get('dimensiones', ''),
            'fecha_ingreso_bodega': fecha_de(bien.get('fecha_ingreso', '')), 'valor_contable': valor_de(bien.get('valor_contable', '')),
        }
        # Un equipo de referencia (de la ficha del área) queda confirmado por bodega: existe y se puede usar.
        if 'Registrado desde la ficha del área' in (equipo.observaciones or ''):
            if equipo.estado_unidad == 'no_disponible':
                equipo.estado_unidad = 'disponible'
            equipo.observaciones = f'Confirmado con el reporte de bienes de bodega (código del bien {codigo}).'
        # El código, el custodio y la ubicación de bodega mandan; lo demás solo llena lo vacío.
        for campo, valor in cambios.items():
            if valor in (None, ''):
                continue
            if campo in ('codigo_bien', 'custodio', 'ubicacion_bodega') or not getattr(equipo, campo):
                setattr(equipo, campo, valor)
        equipo.save()
        tipo = equipo.equipo
        for campo, valor in (('marca', bien.get('marca', '')), ('modelo', bien.get('modelo', ''))):
            if valor and not getattr(tipo, campo):
                setattr(tipo, campo, valor.title() if campo == 'marca' else valor)
                tipo.save(update_fields=[campo])
        return accion, equipo

    @staticmethod
    def _parecido(unidad, area, bien, con_codigo=False):
        """El equipo de la unidad sin código (o, con con_codigo, cualquiera) que mejor coincide con el bien."""
        buscadas = palabras(bien['descripcion'])
        extra = palabras(f"{bien.get('marca', '')} {bien.get('modelo', '')}")
        candidatos = UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True,
        ).select_related('equipo').distinct().order_by('codigo_unidad')
        if not con_codigo:
            candidatos = candidatos.filter(codigo_bien__isnull=True)
        if area is not None:
            candidatos = candidatos.filter(espacios_asociados=area)
        mejor, puntaje_mejor = None, 0.0
        for candidato in candidatos:
            tipo = candidato.equipo
            nombre = palabras(tipo.nombre)
            if se_excluyen(buscadas, nombre):
                continue
            referencia = palabras(f'{tipo.marca or ""} {tipo.modelo or ""} {tipo.caracteristicas_publicas}')
            puntaje = semejanza(buscadas, nombre, extra, referencia)
            if puntaje > puntaje_mejor:
                mejor, puntaje_mejor = candidato, puntaje
        return mejor if puntaje_mejor >= 0.34 else None

    def _nuevo(self, unidad, area, bien, codigo, forzar=False):
        nombre = (bien.get('nombre') or bien['descripcion'].strip().capitalize())[:100]
        # Un bien más de un equipo que el área ya tiene (la tercera secadora) es otra unidad de ese tipo.
        parecido = None if forzar else self._parecido(unidad, area, bien, con_codigo=True)
        tipo = parecido.equipo if parecido else None
        if tipo is None:
            tipo = EquiposServicios.objects.filter(nombre__iexact=nombre, unidades__laboratorio=unidad).first()
        if tipo is None:
            tipo = EquiposServicios.objects.create(
                codigo=siguiente_codigo_modelo(unidad, area), nombre=nombre, estado='disponible', rol='principal',
                marca=bien.get('marca', '').title(), modelo=bien.get('modelo', ''),
                descripcion=f'Registrado desde el reporte de bienes de bodega ({bien["descripcion"].strip().lower()}).',
            )
        asignar_familia(tipo, Counter(), nombre, bien['descripcion'].strip().capitalize())
        if not tipo.icono and tipo.familia_id:
            tipo.icono = tipo.familia.icono
            tipo.save(update_fields=['icono'])
        equipo = UnidadEquipo(codigo_unidad=siguiente_codigo_unidad(unidad, area, tipo), equipo=tipo, laboratorio=unidad,
                              estado_unidad='disponible', criticidad='normal',
                              ubicacion_especifica=area.nombre if area else '')
        equipo.codigo_bien = codigo
        equipo.save()
        equipo.laboratorios.add(unidad)
        if area is not None:
            area.equipos_asociados.add(equipo)
        return equipo
