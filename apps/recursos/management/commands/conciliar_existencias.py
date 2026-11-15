"""Separa en cada unidad los equipos que existen de los que solo son referencia.

Un equipo existe si tiene respaldo: su existencia se verificó, es un bien patrimonial importado del reporte de
bodega (con código y valor contable o fecha de ingreso) o el responsable declaró la cantidad. En una unidad
cuyo inventario patrimonial ya se importó, lo que no tiene respaldo es referencia. En las demás, que todavía no
lo tienen, es referencia lo que la ficha del área describe como de alta capacidad, lo que dice «por verificar»
y lo que nunca se habilitó (no disponible y sin verificar); el equipamiento básico sigue como existencia por
confirmar.

Una referencia no se borra: queda inactiva, fuera del inventario, de los insumos, del visor y de las reservas,
y vuelve a existir al verificarla o al recibirla por compra. Su elemento de la ficha pasa a dotación propuesta
para que la sincronización de fichas no la vuelva a crear. El área que se queda sin ningún equipo existente se
desactiva, igual que las que no pertenecen a la unidad; las decisiones propias de cada unidad están en
catalogos/existencias.py. Solo se tocan los equipos de los que la unidad es dueña.

Simula por defecto; --aplicar guarda. --revertir deshace la última conciliación de cada unidad (equipos, fichas
y áreas; una integración de áreas no se deshace). Repetirla no cambia nada nuevo.
"""
import json
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
from apps.gestion_unidades.presentation.activacion import activar_area, desactivar_area
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.fusion_areas import fusionar_area
from apps.recursos.management.catalogos.existencias import AJENAS, INTEGRACIONES, NOMBRES, VERSION
from apps.recursos.presentation.existencias import por_verificar, respaldo
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import Reserva

NOTA = 'Referencia: {motivo}. Conciliación de existencias del {fecha}; vuelve a existir al verificarla o recibirla.'
ESTADOS_DE_RESERVA_VIGENTE = ('pendiente', 'confirmada', 'en_proceso')


class Command(BaseCommand):
    help = 'Separa los equipos que existen de las referencias y oculta las áreas sin equipos. Simula salvo --aplicar.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', action='append', default=[], help='Slug de la unidad; se puede repetir. Sin esto, todas.')
        parser.add_argument('--aplicar', action='store_true', help='Guarda los cambios. Sin esto solo se simula.')
        parser.add_argument('--revertir', action='store_true', help='Deshace la última conciliación de cada unidad.')
        parser.add_argument('--detalle', action='store_true', help='Lista cada equipo que pasa a referencia.')

    def handle(self, *args, **opciones):
        self.aplicar, self.detalle = opciones['aplicar'], opciones['detalle']
        unidades = Unidad.objects.filter(activo=True).order_by('dependencia', 'nombre')
        if opciones['unidad']:
            unidades = unidades.filter(slug__in=opciones['unidad'])
            faltan = sorted(set(opciones['unidad']) - set(unidades.values_list('slug', flat=True)))
            if faltan:
                raise CommandError('No existen estas unidades activas: ' + ', '.join(faltan))
        total = Counter()
        with transaction.atomic():
            for unidad in unidades:
                unidad = Unidad.objects.select_for_update().get(pk=unidad.pk)
                operar = self.revertir if opciones['revertir'] else self.conciliar
                resumen, avisos = operar(unidad)
                if resumen:
                    self.stdout.write(f'{unidad.nombre}: ' + ', '.join(f'{v} {k}' for k, v in resumen.items()) + '.')
                for aviso in avisos:
                    self.stdout.write(f'  Revisar: {aviso}')
                total.update(resumen)
            if not self.aplicar:
                transaction.set_rollback(True)
        prefijo = 'Aplicado' if self.aplicar else 'Simulación (nada se guardó)'
        self.stdout.write(f'{prefijo}: ' + (', '.join(f'{v} {k}' for k, v in total.items()) or 'nada que cambiar') + '.')

    # ------------------------------------------------------------------ conciliar
    def conciliar(self, unidad):
        resumen, avisos = Counter(), []
        datos = {'equipos': [], 'elementos': [], 'areas': [], 'integradas': []}
        areas = {area.codigo: area for area in EspacioReservable.objects.filter(unidad=unidad)}
        for origen, destino in INTEGRACIONES.get(unidad.slug, ()):
            de, a = areas.get(origen), areas.get(destino)
            if de is None or a is None or de.integrada_en_id or not a.activo:
                continue
            fusionar_area(de, a)
            datos['integradas'].append(de.pk)
            resumen['áreas integradas en otra'] += 1
            nombre = NOMBRES.get((unidad.slug, destino))
            if nombre and a.nombre != nombre:
                a.refresh_from_db()
                a.nombre = nombre
                a.save(update_fields=['nombre'])
        activos = list(UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True, fecha_baja__isnull=True,
        ).distinct().select_related('equipo').prefetch_related('espacios_asociados'))
        if not activos:
            return self._cerrar(unidad, resumen, avisos, datos)
        propios = [equipo for equipo in activos if equipo.laboratorio_id == unidad.pk]
        patrimonial = any(respaldo(equipo) == 'patrimonial' for equipo in activos)
        niveles = self._niveles(unidad)
        ajenas = AJENAS.get(unidad.slug, {})
        areas_activas = {area.pk: area for area in EspacioReservable.objects.filter(unidad=unidad, activo=True)}
        motivos = {}
        for equipo in propios:
            en_areas = {area.pk for area in equipo.espacios_asociados.all() if area.pk in areas_activas}
            ajena = [areas_activas[pk] for pk in en_areas if areas_activas[pk].codigo in ajenas]
            if ajena and len(ajena) == len(en_areas):
                motivos[equipo.pk] = f'su área «{ajena[0].nombre}» no pertenece a la unidad'
                continue
            if respaldo(equipo):
                continue
            nivel = niveles.get(equipo.equipo_id)
            if patrimonial:
                motivos[equipo.pk] = 'no figura en el inventario patrimonial de la unidad'
            elif por_verificar(equipo.equipo.nombre) or nivel == 'por verificar':
                motivos[equipo.pk] = 'la ficha del área lo describe «por verificar»'
            elif nivel == 'alta':
                motivos[equipo.pk] = 'equipamiento de alta capacidad descrito en la ficha del área, sin existencia que lo respalde'
            elif equipo.estado_unidad == 'no_disponible':
                motivos[equipo.pk] = 'nunca se habilitó: no disponible y sin verificar'
        fecha = timezone.localdate().strftime('%d/%m/%Y')
        for equipo in propios:
            motivo = motivos.get(equipo.pk)
            if motivo is None:
                continue
            nota = NOTA.format(motivo=motivo, fecha=fecha)
            equipo.activa = False
            if nota not in (equipo.observaciones or ''):
                equipo.observaciones = f'{equipo.observaciones or ""}\n{nota}'.strip()
            equipo.save(update_fields=['activa', 'observaciones', 'fecha_actualizacion'])
            datos['equipos'].append(equipo.pk)
            resumen['equipos pasan a referencia'] += 1
            if self.detalle:
                self.stdout.write(f'    {equipo.codigo_unidad} · {equipo.equipo.nombre}: {motivo}')
        referencias = set(datos['equipos'])
        existentes = [equipo for equipo in activos if equipo.pk not in referencias]
        # La ficha conserva el equipo como dotación propuesta: la sincronización ya no lo convierte en inventario.
        modelos_en_area = {(area.pk, equipo.equipo_id) for equipo in existentes for area in equipo.espacios_asociados.all()}
        for elemento in ElementoFichaArea.objects.filter(
                ficha__espacio__unidad=unidad, tipo='equipo', solo_referencia=False, registrado_id__in=referencias,
        ).select_related('registrado', 'ficha'):
            if (elemento.ficha.espacio_id, elemento.registrado.equipo_id) in modelos_en_area:
                continue
            elemento.solo_referencia = True
            elemento.save(update_fields=['solo_referencia'])
            datos['elementos'].append(elemento.pk)
            resumen['elementos de ficha pasan a dotación propuesta'] += 1
        con_equipo = {area.pk for equipo in activos for area in equipo.espacios_asociados.all()}
        con_existentes = {area.pk for equipo in existentes for area in equipo.espacios_asociados.all()}
        for area in areas_activas.values():
            if area.codigo in ajenas or (area.pk in con_equipo and area.pk not in con_existentes):
                area.refresh_from_db()
                if area.activo:
                    desactivar_area(area)
                    datos['areas'].append(area.pk)
                    resumen['áreas desactivadas'] += 1
                    if self.detalle:
                        self.stdout.write(f'    Área {area.codigo} · {area.nombre}: '
                                          + (ajenas.get(area.codigo) or 'se queda sin equipos existentes'))
        avisos.extend(self._reservas_afectadas(unidad, referencias, set(datos['areas'])))
        if motivos:
            datos['motivos'] = dict(Counter(motivos.values()))
        return self._cerrar(unidad, resumen, avisos, datos)

    @staticmethod
    def _niveles(unidad):
        """Por modelo: «basico», «alta» o «por verificar», según lo describen las fichas de sus áreas."""
        niveles = {}
        for modelo, nivel, nombre in ElementoFichaArea.objects.filter(
                ficha__espacio__unidad=unidad, tipo='equipo', registrado__isnull=False,
        ).values_list('registrado__equipo_id', 'nivel', 'nombre'):
            propio = 'por verificar' if por_verificar(nombre) else (nivel or 'basico')
            # Basta una descripción básica del modelo para que siga como existencia por confirmar.
            if niveles.get(modelo) != 'basico':
                niveles[modelo] = propio
        return niveles

    @staticmethod
    def _reservas_afectadas(unidad, equipos, areas):
        """Las reservas por venir que piden un equipo o un área que acaba de quedar fuera: no se cancelan solas."""
        avisos = []
        if not equipos and not areas:
            return avisos
        for reserva in Reserva.objects.filter(
                laboratorio=unidad, fecha__gte=timezone.localdate(), estado__in=ESTADOS_DE_RESERVA_VIGENTE,
        ).prefetch_related('espacios_solicitados'):
            try:
                seleccion = json.loads(reserva.unidades_seleccionadas or '[]')
            except (TypeError, ValueError):
                seleccion = []
            ids = {fila.get('id') for fila in seleccion if isinstance(fila, dict)}
            if ids & equipos or {area.pk for area in reserva.espacios_solicitados.all()} & areas:
                avisos.append(f'la reserva {reserva.codigo_reserva or reserva.pk} del {reserva.fecha:%d/%m/%Y} pide '
                              'un equipo o un área que ya no existe; revísala con el solicitante.')
        return avisos

    def _cerrar(self, unidad, resumen, avisos, datos):
        if resumen and self.aplicar:
            registrar_auditoria(
                None, unidad=unidad, accion='actualizar', objeto=unidad,
                descripcion=(f'{VERSION}: {len(datos["equipos"])} equipos pasan a referencia, '
                             f'{len(datos["areas"])} áreas desactivadas, {len(datos["integradas"])} integradas'),
                nuevos=datos)
        return resumen, avisos

    # ------------------------------------------------------------------ revertir
    def revertir(self, unidad):
        resumen, avisos = Counter(), []
        registro = RegistroAuditoriaUnidad.objects.filter(
            unidad=unidad, descripcion__startswith=f'{VERSION}:').order_by('-pk').first()
        if registro is None or RegistroAuditoriaUnidad.objects.filter(
                unidad=unidad, descripcion__startswith=f'{VERSION} revertida', pk__gt=registro.pk).exists():
            return resumen, avisos
        datos = registro.datos_nuevos or {}
        for equipo in UnidadEquipo.objects.filter(pk__in=datos.get('equipos', []), activa=False, fecha_baja__isnull=True):
            equipo.activa = True
            lineas = [linea for linea in (equipo.observaciones or '').splitlines()
                      if not (linea.startswith('Referencia: ') and 'Conciliación de existencias' in linea)]
            equipo.observaciones = '\n'.join(lineas)
            equipo.save(update_fields=['activa', 'observaciones', 'fecha_actualizacion'])
            resumen['equipos vuelven a existir'] += 1
        resumen['elementos de ficha vuelven a dotación'] += ElementoFichaArea.objects.filter(
            pk__in=datos.get('elementos', []), solo_referencia=True).update(solo_referencia=False)
        for area in EspacioReservable.objects.filter(pk__in=datos.get('areas', []), activo=False, integrada_en__isnull=True):
            activar_area(area)
            resumen['áreas reactivadas'] += 1
        if datos.get('integradas'):
            avisos.append('las integraciones de áreas no se deshacen; se revisan una por una desde la gestión.')
        resumen = +resumen
        if self.aplicar and resumen:
            registrar_auditoria(
                None, unidad=unidad, accion='actualizar', objeto=unidad,
                descripcion=f'{VERSION} revertida: {resumen.get("equipos vuelven a existir", 0)} equipos vuelven a existir',
                nuevos={'revierte': registro.pk, **dict(resumen)})
        return resumen, avisos
