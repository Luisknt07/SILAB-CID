"""Lleva los códigos del sistema al estándar UNIDAD-ÁREA-MODELO-N.º en todas las unidades.

Cada unidad física toma el código de su unidad dueña y de su área principal (FAB-IMP3D-05-02); cada modelo, el
de la unidad y el área donde tiene más equipos (FAB-IMP3D-05). Lo que ya cumple el estándar no se toca y los
números libres se asignan en el orden de los códigos actuales, así que correrlo otra vez no cambia nada. Los
códigos anteriores quedan como alias, la historia de cada equipo registra el cambio y las reservas pasan a
nombrar el código nuevo. --simular muestra lo que haría sin guardar nada.
"""
import json
import re
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.presentation.codigos_sistema import sigla_de_area, sigla_de_unidad
from apps.recursos.models.equipos import AliasCodigoEquipoServicio, EquiposServicios
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad


class Simulacion(Exception):
    """Deshace todo al final de una simulación."""


def orden_natural(texto):
    """Primero lo que sigue la numeración de las fichas de área (FAB-A2-05-01: modelo 5, unidad 1), en ese orden;
    después lo demás (BIEN-…, códigos antiguos o de ejemplo), en orden natural."""
    ficha = re.match(r'^[A-Z]+-A\d+-(\d+)-(\d+)$', texto or '')
    if ficha:
        return (0, int(ficha.group(1)), int(ficha.group(2)), [])
    return (1, 0, 0, [(0, int(parte), '') if parte.isdigit() else (1, 0, parte) for parte in re.split(r'(\d+)', texto or '')])


def libres(usados):
    """Los números 1, 2, 3… que no están en usados, a medida que se piden."""
    numero = 0
    while True:
        numero += 1
        if numero not in usados:
            usados.add(numero)
            yield numero


class Command(BaseCommand):
    help = 'Lleva los códigos de equipos y modelos al estándar UNIDAD-ÁREA-MODELO-N.º (con alias de los anteriores).'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', action='append', help='Slug de la unidad; se puede repetir.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        unidades = Unidad.objects.order_by('nombre')
        if opciones['unidad']:
            unidades = unidades.filter(slug__in=opciones['unidad'])
        alias_unidad = set(AliasCodigoUnidadEquipo.objects.values_list('codigo', flat=True))
        alias_modelo = set(AliasCodigoEquipoServicio.objects.values_list('codigo', flat=True))
        nuevos_unidad, hogares = {}, defaultdict(Counter)
        for unidad in unidades:
            self._unidad(unidad, alias_unidad, nuevos_unidad, hogares)
        nuevos_modelo = self._modelos(hogares, {unidad.pk for unidad in unidades}, alias_modelo, bool(opciones['unidad']))
        resumen = Counter()
        try:
            with transaction.atomic():
                self._renombrar_unidades(nuevos_unidad, resumen)
                self._renombrar_modelos(nuevos_modelo, resumen)
                self._actualizar_reservas(nuevos_unidad, resumen)
                if opciones['simular']:
                    raise Simulacion
        except Simulacion:
            pass
        for equipo, (anterior, nuevo) in list(nuevos_unidad.items())[:12]:
            self.stdout.write(f'  {anterior:>24} -> {nuevo}')
        prefijo = '[simulación] ' if opciones['simular'] else ''
        detalle = ', '.join(f'{valor} {clave}' for clave, valor in sorted(resumen.items())) or 'todo ya estaba en el estándar'
        self.stdout.write(self.style.SUCCESS(f'{prefijo}{detalle}'))

    def _unidad(self, unidad, alias_unidad, nuevos, hogares):
        sigla = sigla_de_unidad(unidad)
        equipos = list(UnidadEquipo.objects.filter(laboratorio=unidad).select_related('equipo')
                       .prefetch_related('espacios_asociados'))
        # Por sigla de área (no por área): dos áreas con la misma sigla comparten la numeración y no se repite un código.
        por_area = defaultdict(list)
        for equipo in equipos:
            propias = sorted((espacio for espacio in equipo.espacios_asociados.all() if espacio.unidad_id == unidad.pk),
                             key=lambda espacio: (espacio.orden, espacio.nombre))
            por_area[sigla_de_area(propias[0] if propias else None)].append(equipo)
        for sigla_area, lista in por_area.items():
            base = f'{sigla}-{sigla_area}-'
            estandar = re.compile(rf'^{re.escape(base)}(\d{{2,}})-(\d{{2,}})$')
            # Lo que ya cumple: cada número de modelo es de un solo modelo y cada modelo tiene un número.
            modelo_de_numero, numero_de_modelo = {}, {}
            for equipo in sorted(lista, key=lambda item: orden_natural(item.codigo_unidad)):
                coincidencia = estandar.match(equipo.codigo_unidad)
                if not coincidencia:
                    continue
                numero = int(coincidencia.group(1))
                if modelo_de_numero.setdefault(numero, equipo.equipo_id) == equipo.equipo_id:
                    numero_de_modelo.setdefault(equipo.equipo_id, numero)
            usados_modelo = set(modelo_de_numero) | {
                int(coincidencia.group(1)) for coincidencia in
                (re.match(rf'^{re.escape(base)}(\d+)', codigo) for codigo in alias_unidad) if coincidencia}
            numeros = libres(usados_modelo)
            por_modelo = defaultdict(list)
            for equipo in lista:
                por_modelo[equipo.equipo_id].append(equipo)
            for tipo_id, propios in sorted(por_modelo.items(),
                                           key=lambda par: min(orden_natural(item.codigo_unidad) for item in par[1])):
                if tipo_id not in numero_de_modelo:
                    numero_de_modelo[tipo_id] = next(numeros)
                modelo = f'{base}{numero_de_modelo[tipo_id]:02d}'
                hogares[tipo_id][modelo] += len(propios)
                patron = re.compile(rf'^{re.escape(modelo)}-(\d{{2,}})$')
                validos = {equipo.pk for equipo in propios if patron.match(equipo.codigo_unidad)}
                usados = {int(patron.match(equipo.codigo_unidad).group(1)) for equipo in propios if equipo.pk in validos}
                usados |= {int(coincidencia.group(1)) for coincidencia in map(patron.match, alias_unidad) if coincidencia}
                correlativos = libres(usados)
                for equipo in sorted(propios, key=lambda item: orden_natural(item.codigo_unidad)):
                    if equipo.pk not in validos:
                        nuevos[equipo] = (equipo.codigo_unidad, f'{modelo}-{next(correlativos):02d}')

    @staticmethod
    def _modelos(hogares, procesadas, alias_modelo, parcial):
        """Cada modelo toma el código del área donde tiene más equipos; con --unidad, solo los que no son de otras."""
        nuevos = {}
        tipos = EquiposServicios.objects.in_bulk(list(hogares))
        for tipo_id, conteo in hogares.items():
            tipo = tipos[tipo_id]
            if parcial and UnidadEquipo.objects.filter(equipo=tipo).exclude(laboratorio_id__in=procesadas).exists():
                continue
            codigo = conteo.most_common(1)[0][0]
            if tipo.codigo != codigo and codigo not in alias_modelo:
                nuevos[tipo] = (tipo.codigo, codigo)
        return nuevos

    @staticmethod
    def _renombrar_unidades(nuevos, resumen):
        if not nuevos:
            return
        # En dos pasos para no chocar con el índice único mientras unos toman el código que otros dejan.
        for equipo in nuevos:
            UnidadEquipo.objects.filter(pk=equipo.pk).update(codigo_unidad=f'TMP-ESTANDAR-{equipo.pk}')
        for equipo, (anterior, nuevo) in nuevos.items():
            UnidadEquipo.objects.filter(pk=equipo.pk).update(codigo_unidad=nuevo)
        AliasCodigoUnidadEquipo.objects.bulk_create(
            [AliasCodigoUnidadEquipo(codigo=anterior, unidad_equipo_id=equipo.pk) for equipo, (anterior, _n) in nuevos.items()],
            ignore_conflicts=True)
        EventoCicloVidaEquipo.objects.bulk_create([EventoCicloVidaEquipo(
            equipo_id=equipo.pk, unidad_id=equipo.laboratorio_id, tipo='cambio_codigo',
            descripcion=f'Código del sistema cambiado de {anterior} a {nuevo} (estándar UNIDAD-ÁREA-MODELO-N.º).',
        ) for equipo, (anterior, nuevo) in nuevos.items()])
        resumen['unidades físicas recodificadas'] = len(nuevos)

    @staticmethod
    def _renombrar_modelos(nuevos, resumen):
        if not nuevos:
            return
        for tipo in nuevos:
            EquiposServicios.objects.filter(pk=tipo.pk).update(codigo=f'TMP{tipo.pk}'[:20])
        for tipo, (anterior, nuevo) in nuevos.items():
            EquiposServicios.objects.filter(pk=tipo.pk).update(codigo=nuevo)
        AliasCodigoEquipoServicio.objects.bulk_create(
            [AliasCodigoEquipoServicio(codigo=anterior, modelo_id=tipo.pk) for tipo, (anterior, _n) in nuevos.items()],
            ignore_conflicts=True)
        resumen['modelos recodificados'] = len(nuevos)

    @staticmethod
    def _actualizar_reservas(nuevos, resumen):
        """Las reservas guardan el código del equipo: pasan al nuevo para que agenda, uso y disponibilidad sigan."""
        mapa = {anterior: nuevo for anterior, nuevo in nuevos.values()}
        if not mapa:
            return
        cambiadas = []
        for reserva in Reserva.objects.only('pk', 'unidades_seleccionadas', 'equipo_codigo').iterator():
            cambio = False
            if reserva.equipo_codigo in mapa:
                reserva.equipo_codigo, cambio = mapa[reserva.equipo_codigo], True
            try:
                seleccion = json.loads(reserva.unidades_seleccionadas or '[]')
            except ValueError:
                seleccion = None
            if isinstance(seleccion, list):
                for item in seleccion:
                    if isinstance(item, dict) and item.get('codigo') in mapa:
                        item['codigo'], cambio = mapa[item['codigo']], True
                if cambio:
                    reserva.unidades_seleccionadas = json.dumps(seleccion, ensure_ascii=False)
            if cambio:
                cambiadas.append(reserva)
        Reserva.objects.bulk_update(cambiadas, ['unidades_seleccionadas', 'equipo_codigo'], batch_size=500)
        resumen['reservas actualizadas'] = len(cambiadas)
