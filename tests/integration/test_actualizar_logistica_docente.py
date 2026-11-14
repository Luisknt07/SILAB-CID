"""La actualización docente conserva identificadores y datos operativos."""
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, NOMBRE, NOMBRE_CORTO, SLUG
from apps.formacion.models.asignaturas import Asignatura
from apps.formacion.models.cursos import Curso
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.gestion_unidades.models.presentacion import PresentacionUnidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class ActualizarLogisticaDocenteTests(TestCase):
    def setUp(self):
        self.carpeta = TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        self.enterContext(override_settings(BASE_DIR=Path(self.carpeta.name)))
        self.unidad = Unidad.objects.create(slug=SLUG, nombre='Nombre anterior', nombre_corto='Business Lab',
                                           descripcion='Descripción anterior', fecha_inicio=date(2025, 1, 1))
        for codigo, datos in AREAS.items():
            EspacioReservable.objects.create(unidad=self.unidad, codigo=codigo, nombre=datos['anterior'],
                                             capacidad=8, reservable=False, politica_reserva='tecnico')
        self.area = self.unidad.espacios_reservables.get(codigo='LOG-ALMACEN')
        equipo = EquiposServicios.objects.create(codigo='LOG-LECTOR', nombre='Lector')
        self.equipo = UnidadEquipo.objects.create(laboratorio=self.unidad, equipo=equipo, codigo_unidad='LOG-LECTOR-01')
        self.area.equipos_asociados.add(self.equipo)
        FichaArea.objects.create(espacio=self.area, que_es='Contenido propio', publicada=True)
        PresentacionUnidad.objects.create(unidad=self.unidad, publicada=True, video_presenta='Docente')
        self.curso = Curso.objects.create(unidad=self.unidad, codigo='LOG-CUR-PRUEBA', nombre='Curso que se conserva')
        self.asignatura = Asignatura.objects.create(
            unidad=self.unidad, codigo='LOG-RUTAS', nombre='Diseño de rutas',
            descripcion='Se practica en el área «Transporte, distribución y última milla». Fuente: malla.',
        )
        self.otra = Unidad.objects.create(slug='otra-unidad', nombre='Otra unidad', descripcion='Otro contenido',
                                         fecha_inicio=date(2025, 1, 1))

    def correr(self, **opciones):
        salida = StringIO()
        call_command('actualizar_logistica_docente', stdout=salida, **opciones)
        return salida.getvalue()

    def test_actualiza_sin_cambiar_identificadores_equipos_cursos_ni_politicas(self):
        ids = dict(self.unidad.espacios_reservables.values_list('codigo', 'pk'))
        self.correr()
        self.unidad.refresh_from_db()
        self.area.refresh_from_db()
        self.curso.refresh_from_db()
        self.otra.refresh_from_db()
        self.assertEqual((self.unidad.nombre, self.unidad.nombre_corto, self.unidad.slug), (NOMBRE, NOMBRE_CORTO, SLUG))
        self.assertEqual(dict(self.unidad.espacios_reservables.values_list('codigo', 'pk')), ids)
        self.assertEqual((self.area.capacidad, self.area.reservable, self.area.politica_reserva), (8, False, 'tecnico'))
        self.assertEqual(list(self.area.equipos_asociados.all()), [self.equipo])
        self.assertEqual((self.area.ficha.que_es, self.area.ficha.publicada), ('Contenido propio', True))
        self.assertTrue(self.unidad.presentacion.publicada)
        self.assertEqual(self.unidad.presentacion.video_presenta, 'Docente')
        self.assertEqual(self.curso.nombre, 'Curso que se conserva')
        self.assertEqual(self.otra.nombre, 'Otra unidad')
        self.asignatura.refresh_from_db()
        self.assertIn('«Transporte, distribución y movilidad»', self.asignatura.descripcion)
        self.assertEqual(len(list(Path(self.carpeta.name).rglob('logistica-docente-*.json'))), 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).count(), 1)
        self.assertIn('sin cambios', self.correr())
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).count(), 1)

    def test_simular_no_guarda_datos_ni_archivos(self):
        self.assertIn('[simulación]', self.correr(simular=True))
        self.unidad.refresh_from_db()
        self.area.refresh_from_db()
        self.assertEqual(self.unidad.nombre, 'Nombre anterior')
        self.assertEqual(self.area.nombre, AREAS['LOG-ALMACEN']['anterior'])
        self.assertFalse(list(Path(self.carpeta.name).rglob('*.json')))
        self.assertFalse(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).exists())

    def test_area_ausente_impide_una_actualizacion_parcial(self):
        self.unidad.espacios_reservables.get(codigo='LOG-AREA-ERP').delete()
        with self.assertRaisesMessage(CommandError, 'Faltan áreas existentes'):
            self.correr()
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.nombre, 'Nombre anterior')
        self.assertFalse(list(Path(self.carpeta.name).rglob('*.json')))
