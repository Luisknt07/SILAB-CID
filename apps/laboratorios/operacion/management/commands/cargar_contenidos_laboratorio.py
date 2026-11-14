"""Carga en borrador los contenidos de referencia de FabLab, Robótica y Realidad Extendida.

Procesos, productos, software, recursos en línea y cursos de cada laboratorio, tomados de la
investigación de equipamiento (ver `apps/laboratorios/operacion/management/laboratorios/contenidos.py`). Nada queda
publicado: el laboratorio revisa cada elemento en su ficha, donde lo ve marcado como borrador,
y lo activa en el editor.

Es idempotente: lo que ya existe (por código o por nombre) se conserva tal como el laboratorio
lo haya dejado, aunque lo haya corregido. `--simular` muestra lo que haría sin guardar nada.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.fusion_areas import area_vigente
from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de
from apps.laboratorios.operacion.management.laboratorios.contenidos import CONTENIDOS, FUENTE, NOTA_TIEMPOS
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.reservas.models.reservas import CatalogoActividadReserva
from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, InsumoReceta, Producto, Receta
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

CARPETA_RECURSOS = 'Recursos en línea recomendados'


class Simulacion(Exception):
    """Deshace la carga al final de una simulación."""


class Command(BaseCommand):
    help = 'Carga en borrador los procesos, productos, software, recursos y cursos de referencia de los laboratorios.'

    def add_arguments(self, parser):
        parser.add_argument('--laboratorio', action='append', choices=sorted(CONTENIDOS),
                            help='Solo este laboratorio; se puede repetir.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        for slug in opciones['laboratorio'] or CONTENIDOS:
            unidad = Unidad.objects.filter(slug=slug).first()
            if unidad is None:
                self.stdout.write(self.style.WARNING(f'{slug}: no existe; se omite.'))
                continue
            try:
                with transaction.atomic():
                    resumen, avisos = self._cargar(unidad, CONTENIDOS[slug])
                    if opciones['simular']:
                        raise Simulacion
                    if sum(resumen.values()):
                        registrar_auditoria(
                            None, unidad=unidad, accion='actualizar', objeto=unidad,
                            descripcion='Carga en borrador de contenidos de referencia (Fase 4)',
                            nuevos=dict(resumen),
                        )
            except Simulacion:
                pass
            prefijo = '[simulación] ' if opciones['simular'] else ''
            creados = ', '.join(f'{cantidad} {nombre}' for nombre, cantidad in resumen.items() if cantidad) or 'nada nuevo'
            self.stdout.write(self.style.SUCCESS(f'{prefijo}{unidad.nombre}: {creados}.'))
            for aviso in avisos:
                self.stdout.write(f'  aviso: {aviso}')

    def _cargar(self, unidad, contenido):
        resumen, avisos = Counter(), []
        for nombre, acceso, descripcion in contenido['software']:
            _software, creado = SoftwareDisponible.objects.get_or_create(
                unidad=unidad, nombre=nombre,
                defaults={'tipo_acceso': acceso, 'descripcion': descripcion, 'activo': False,
                          'instrucciones_acceso': 'Propuesto como referencia; se activa al confirmar que está instalado.'},
            )
            resumen['programas'] += creado
        productos = {}
        for codigo, nombre, medida, descripcion in contenido['productos']:
            productos[codigo], creado = Producto.objects.get_or_create(
                unidad=unidad, codigo=codigo,
                defaults={'nombre': nombre, 'unidad_medida': medida, 'descripcion': descripcion, 'tipo': 'terminado',
                          'publico': False},
            )
            resumen['productos'] += creado
        # Un área fusionada entrega sus etapas a la que la integró.
        areas = {area.codigo: area_vigente(area) for area in EspacioReservable.objects.filter(unidad=unidad)}
        equipos = {equipo.codigo_unidad: equipo.equipo for equipo in
                   UnidadEquipo.objects.filter(laboratorio=unidad).select_related('equipo')}
        insumos = {consumible.codigo: consumible for consumible in Consumible.objects.filter(unidad=unidad)}
        for definicion in contenido['procesos']:
            if Receta.objects.filter(unidad=unidad, codigo=definicion['codigo']).exists():
                continue
            self._proceso(unidad, definicion, productos, areas, equipos, insumos, avisos)
            resumen['procesos'] += 1
        resumen['recursos en línea'] += self._recursos(unidad, contenido['recursos'])
        for nombre, subtipo, descripcion in contenido['cursos']:
            _curso, creado = CatalogoActividadReserva.objects.get_or_create(
                unidad=unidad, nombre=nombre, proposito_codigo='capacitacion',
                defaults={'subtipo_actividad': subtipo, 'descripcion': descripcion, 'estado_publicacion': 'borrador',
                          'visibilidad': 'institucional'},
            )
            resumen['cursos'] += creado
        return resumen, avisos

    def _proceso(self, unidad, definicion, productos, areas, equipos, insumos, avisos):
        producto = productos[definicion['producto']]
        minutos = sum(paso['minutos'] for paso in definicion['etapas'])
        receta = Receta.objects.create(
            unidad=unidad, producto=producto, codigo=definicion['codigo'], nombre=definicion['nombre'],
            cantidad_base=1, unidad_base=producto.unidad_medida, rendimiento_esperado=1,
            duracion_horas=round(minutos / 60, 2),
            instrucciones=f'{definicion["instrucciones"]}\n\n{NOTA_TIEMPOS} Fuente: {FUENTE}.',
            origen='referencia', activa=False,
        )
        for orden, paso in enumerate(definicion['etapas'], start=1):
            area = areas.get(paso['area'])
            if area is None:
                avisos.append(f'{receta.codigo}: el área {paso["area"]} no existe; la etapa «{paso["nombre"]}» queda sin área.')
            equipo = equipos.get(paso['equipo']) if paso['equipo'] else None
            if paso['equipo'] and equipo is None:
                avisos.append(f'{receta.codigo}: el equipo {paso["equipo"]} no está registrado; la etapa queda sin equipo.')
            etapa = EtapaReceta.objects.create(
                receta=receta, orden=orden, nombre=paso['nombre'], tipo=paso['tipo'], espacio=area, equipo=equipo,
                duracion_min=paso['minutos'], instrucciones=paso['instrucciones'], parametro=paso['parametro'],
                limite=paso['limite'], punto_control=bool(paso['parametro']),
            )
            for codigo, cantidad in paso['insumos']:
                if codigo not in insumos:
                    avisos.append(f'{receta.codigo}: el insumo {codigo} no está en el inventario; no se enlaza.')
                    continue
                InsumoReceta.objects.create(receta=receta, etapa=etapa, consumible=insumos[codigo], cantidad=cantidad)
        receta.software.set(SoftwareDisponible.objects.filter(unidad=unidad, nombre__in=definicion['software']))

    @staticmethod
    def _recursos(unidad, recursos):
        """Los enlaces van a una carpeta interna de la sección de recursos de aprendizaje."""
        mapa = mapa_de(unidad)
        numero = mapa.numero('recursos_aprendizaje') if mapa else ''
        modulo = unidad.modulos_contenido.filter(clave=mapa.modulo_de(numero)).first() if numero else None
        carpeta, _ = CarpetaRecurso.objects.get_or_create(
            unidad=unidad, nombre=CARPETA_RECURSOS, carpeta_padre=None,
            defaults={'modulo': 'recursos', 'modulo_config': modulo, 'seccion_planta': numero,
                      'visibilidad': 'interna', 'activa': True, 'orden': 50},
        )
        creados = 0
        for orden, (nombre, url, descripcion) in enumerate(recursos, start=1):
            _recurso, creado = Recurso.objects.get_or_create(
                unidad=unidad, carpeta=carpeta, nombre=nombre,
                defaults={'url': url, 'descripcion': descripcion, 'visibilidad': 'interna', 'activo': True,
                          'orden': orden, 'fuente': 'externa'},
            )
            creados += creado
        return creados
