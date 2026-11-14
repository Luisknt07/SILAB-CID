"""Actualiza solo la identidad y las áreas docentes de Logística, conservando su operación."""
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, DESCRIPCION, DESCRIPCION_CORTA, NOMBRE, NOMBRE_CORTO, PRESENTACION, SLUG
from apps.gestion_unidades.models.presentacion import PresentacionUnidad
from apps.directorio_unidades.models.core import Unidad

# Solo las líneas sembradas por el cargador anterior; las escritas por la unidad se conservan.
LINEAS_ANTERIORES = (
    'Minialmacén didáctico', 'Simulación de cadena', 'Transporte y ruteo',
    'Negociación', 'Comercio internacional', 'ERP y analítica', 'Formación práctica',
)


class Command(BaseCommand):
    help = 'Actualiza nombre, áreas y presentación docente de Logística, con respaldo previo.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra cambios sin guardarlos ni crear archivos.')

    @transaction.atomic
    def handle(self, *args, **opciones):
        unidad = Unidad.objects.select_for_update().filter(slug=SLUG).first()
        if unidad is None:
            raise CommandError('No existe el laboratorio de Logística; no se crea otra unidad.')
        areas = {area.codigo: area for area in unidad.espacios_reservables.select_for_update()}
        faltan = set(AREAS) - areas.keys()
        if faltan:
            raise CommandError('Faltan áreas existentes: ' + ', '.join(sorted(faltan)))
        if any(areas[codigo].integrada_en_id for codigo in AREAS):
            raise CommandError('Una de las seis áreas está integrada en otra; revise su estructura antes de actualizar.')
        presentacion = PresentacionUnidad.objects.filter(unidad=unidad).first()
        lineas = list(unidad.lineas_accion.all())
        asignaturas = list(unidad.asignaturas.all())
        anteriores = {'nombre': unidad.nombre, 'nombre_corto': unidad.nombre_corto,
                      'areas': {codigo: areas[codigo].nombre for codigo in AREAS}}
        if not opciones['simular']:
            objetos = [unidad, *areas.values(), *lineas, *asignaturas]
            if presentacion:
                objetos.append(presentacion)
            carpeta = Path(settings.BASE_DIR) / 'var' / 'backups'
            carpeta.mkdir(parents=True, exist_ok=True)
            respaldo = carpeta / ('logistica-docente-' + timezone.now().strftime('%Y%m%dT%H%M%S%f') + '.json')
            respaldo.write_text(serializers.serialize('json', objetos, indent=2, ensure_ascii=False), encoding='utf-8')
            self.stdout.write(f'Respaldo: {respaldo}')
        resumen = Counter()
        resumen['identidad'] += self._actualizar(unidad, {
            'nombre': NOMBRE, 'nombre_corto': NOMBRE_CORTO,
            'descripcion': DESCRIPCION, 'descripcion_corta': DESCRIPCION_CORTA,
        })
        for orden, (codigo, datos) in enumerate(AREAS.items(), start=1):
            resumen['áreas'] += self._actualizar(areas[codigo], {
                'nombre': datos['nombre'], 'descripcion_publica': datos['descripcion'], 'orden': orden,
            })
        if presentacion:
            valores = {campo: '\n'.join(valor) if isinstance(valor, list) else valor
                       for campo, valor in PRESENTACION.items() if campo != 'lineas'}
            resumen['presentación'] += self._actualizar(presentacion, valores)
        for orden, (anterior, definicion) in enumerate(zip(LINEAS_ANTERIORES, PRESENTACION['lineas']), start=1):
            titulo, icono, descripcion = definicion
            linea = next((fila for fila in lineas if fila.titulo in (anterior, titulo)), None)
            if linea:
                resumen['líneas docentes'] += self._actualizar(linea, {
                    'titulo': titulo, 'icono': icono, 'descripcion': descripcion, 'orden': orden,
                })
        for asignatura in asignaturas:
            descripcion = asignatura.descripcion
            for datos in AREAS.values():
                descripcion = descripcion.replace('«' + datos['anterior'] + '»', '«' + datos['nombre'] + '»')
            resumen['referencias de asignaturas'] += self._actualizar(asignatura, {'descripcion': descripcion})
        if opciones['simular']:
            transaction.set_rollback(True)
        elif sum(resumen.values()):
            registrar_auditoria(
                unidad=unidad, accion='actualizar', objeto=unidad,
                descripcion='Actualización de identidad y seis áreas docentes de Logística', anteriores=anteriores,
                nuevos={'nombre': NOMBRE, 'nombre_corto': NOMBRE_CORTO,
                        'areas': {codigo: datos['nombre'] for codigo, datos in AREAS.items()}},
            )
        detalle = ', '.join(f'{cantidad} {campo}' for campo, cantidad in resumen.items() if cantidad) or 'sin cambios'
        prefijo = '[simulación] ' if opciones['simular'] else ''
        self.stdout.write(self.style.SUCCESS(prefijo + detalle + '.'))

    @staticmethod
    def _actualizar(objeto, valores):
        cambios = {campo: valor for campo, valor in valores.items() if getattr(objeto, campo) != valor}
        for campo, valor in cambios.items():
            setattr(objeto, campo, valor)
        if cambios:
            objeto.save(update_fields=list(cambios))
        return bool(cambios)
