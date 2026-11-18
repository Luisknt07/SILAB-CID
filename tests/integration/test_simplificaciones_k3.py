"""Incidentes de seguridad sin equipo y con la fecha del hecho; calibración de cada equipo físico.

Un incidente de seguridad (una caída, un derrame) no siempre involucra un equipo, ni se reporta el día en que pasa.
Y la calibración es de cada equipo físico: dos balanzas del mismo modelo no se calibran el mismo día. Completar la
orden de calibración pone sola las fechas y el certificado del equipo, y deja rastro.
"""
from datetime import date, datetime, time, timedelta
from importlib import import_module
from io import StringIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.apps import apps as registro_de_apps
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.reportes_auditoria import reporte_calibracion
from apps.gestion_unidades.presentation.reportes_conteo import _calibracion
from apps.gestion_unidades.presentation.tablero_operativo import construir_tablero_operativo
from apps.integraciones.management.commands.limpiar_movimientos import FRASE
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import (
    EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo,
)
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.reportes_mantenimiento import reporte_mantenimiento
from tests.integration.test_rutas_de_captura_seguridad_resultados_principales import BaseDeRutas

INCIDENTES = import_module('apps.recursos.migrations.0009_incidentes_de_seguridad_sin_equipo')
CALIBRACION = import_module('apps.recursos.migrations.0010_calibracion_por_equipo_fisico')


def _a_las(dia, hora=10):
    return timezone.make_aware(datetime.combine(dia, time(hora)))


class IncidentesDeSeguridadSinEquipoTests(BaseDeRutas):

    def incidente(self, **datos):
        base = dict(tipo='seguridad', unidad=self.unidad, titulo='Derrame ficticio sin equipo',
                    descripcion='Derrame menor de agua en el área.', reportada_por=self.cuenta)
        return IncidenciaEquipo.objects.create(**(base | datos))

    def test_editar_desde_el_panel_un_incidente_sin_equipo_lo_resuelve(self):
        base = dict(modulo='incidencia', equipo_id='', tipo='seguridad', prioridad='baja', estado='abierta',
                    titulo='Tropiezo ficticio', descripcion='Sin lesiones.', espacio_id=self.espacio.pk,
                    asignada_a='', solucion='', fecha_hecho='')
        self.assertEqual(self.operar(**base).status_code, 200)
        incidente = IncidenciaEquipo.objects.get(titulo='Tropiezo ficticio')
        hecho = incidente.fecha_hecho
        respuesta = self.operar(**(base | dict(registro_id=incidente.pk, estado='resuelta',
                                               solucion='Se señalizó el desnivel.')))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        incidente.refresh_from_db()
        self.assertEqual((incidente.estado, incidente.espacio, incidente.fecha_hecho), ('resuelta', self.espacio, hecho))
        # Sin equipo no hay ciclo de vida que anotar, pero la auditoría de la unidad sí lo registra.
        self.assertFalse(EventoCicloVidaEquipo.objects.filter(incidencia=incidente).exists())
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            unidad=self.unidad, entidad='recursos.IncidenciaEquipo', objeto_id=str(incidente.pk)).exists())

    def test_ninguna_consulta_pierde_los_incidentes_sin_equipo(self):
        incidente = self.incidente(espacio=self.espacio)
        self.assertEqual(str(incidente), f'{self.espacio.nombre} · Derrame ficticio sin equipo')
        configuracion = SimpleNamespace(incidencias_equipos=True, mantenimiento_equipos=True, consumibles=True)
        self.assertEqual(construir_tablero_operativo(self.unidad, configuracion)['incidencias_abiertas'], 1)
        _encabezados, _filas, tarjetas, _semaforos = reporte_mantenimiento(self.unidad, self.hoy, self.hoy)
        tarjetas = {tarjeta[0]: tarjeta[1] for tarjeta in tarjetas}
        self.assertEqual(tarjetas['Incidencias del período'], 1)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})
        self.assertContains(panel, 'Derrame ficticio sin equipo')
        self.assertContains(panel, f'{self.espacio.nombre} · Seguridad')

    def test_la_limpieza_de_movimientos_borra_el_incidente_sin_equipo_y_conserva_el_espacio(self):
        self.incidente(espacio=self.espacio)
        self.incidente(titulo='Caída ficticia en la unidad')
        call_command('limpiar_movimientos', '--aplicar', '--confirmar', FRASE, '--base',
                     connection.settings_dict['NAME'], stdout=StringIO())
        self.assertFalse(IncidenciaEquipo.objects.exists())
        self.assertTrue(type(self.espacio).objects.filter(pk=self.espacio.pk).exists())

    def test_el_modelo_exige_equipo_a_la_tecnica_y_rechaza_la_fecha_futura(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as error:
            self.incidente(tipo='falla')
        self.assertIn('equipo', error.exception.message_dict)
        with self.assertRaises(ValidationError) as error:
            self.incidente(fecha_hecho=timezone.now() + timedelta(days=1))
        self.assertIn('fecha_hecho', error.exception.message_dict)
        with self.assertRaises(ValidationError) as error:
            self.incidente(detiene_operacion=True)
        self.assertIn('detiene_operacion', error.exception.message_dict)
        self.assertFalse(IncidenciaEquipo.objects.exists())

    def test_la_migracion_conserva_las_fechas_que_ya_tienen_las_incidencias(self):
        ayer = timezone.now() - timedelta(days=1)
        incidente = self.incidente(equipo=self.equipo, tipo='falla', fecha_hecho=ayer)
        INCIDENTES.fecha_del_hecho_desde_el_reporte(registro_de_apps, None)
        incidente.refresh_from_db()
        self.assertEqual((incidente.fecha_hecho, incidente.equipo, incidente.unidad), (ayer, self.equipo, self.unidad))


class CalibracionPorEquipoFisicoTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        responsable = get_user_model().objects.create_user('responsable.calibracion-k3', password=None)
        cls.responsable = responsable
        cls.unidad = Unidad.objects.create(nombre='Laboratorio ficticio de calibración K3', slug='laboratorio-cal-k3',
                                           dependencia='laboratorios', administrador=responsable,
                                           fecha_inicio=date(2025, 1, 1))
        cls.modelo = EquiposServicios.objects.create(nombre='Balanza ficticia K3', codigo='MOD-K3-BAL')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='calibracion-k3-', ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)

    def equipo(self, codigo, **datos):
        return UnidadEquipo.objects.create(codigo_unidad=codigo, laboratorio=self.unidad, equipo=self.modelo, **datos)

    def completar_calibracion(self, equipo, dia, **datos):
        orden = MantenimientoEquipo.objects.create(
            equipo=equipo, tipo='calibracion', estado='programado', titulo='Calibración ficticia K3',
            fecha_programada=_a_las(dia, 8), responsable=self.responsable, **datos)
        orden.estado, orden.fecha_inicio, orden.fecha_fin = 'completado', _a_las(dia, 8), _a_las(dia, 9)
        orden.resultado = 'Calibrada con pesas patrón ficticias.'
        orden.informe = ContentFile(b'%PDF-1.4 certificado ficticio K3', name='certificado-k3.pdf')
        orden.save()
        equipo.refresh_from_db()
        return orden

    def test_dos_equipos_del_mismo_modelo_tienen_su_propia_calibracion(self):
        self.equipo('K3-BAL-01', ultima_calibracion=date(2026, 1, 10), proxima_calibracion=date(2027, 1, 10))
        self.equipo('K3-BAL-02', ultima_calibracion=date(2025, 3, 5), proxima_calibracion=date(2026, 3, 5))
        self.equipo('K3-BAL-03')
        filas = reporte_calibracion(self.unidad, date(2026, 1, 1), date(2026, 6, 30))['rows']
        self.assertEqual([fila[:4] for fila in filas], [
            ['K3-BAL-01 · Balanza ficticia K3', '10/01/2026', '10/01/2027', 'Vigente'],
            ['K3-BAL-02 · Balanza ficticia K3', '05/03/2025', '05/03/2026', 'Vencida'],
        ])
        self.assertEqual(_calibracion(self.unidad, date(2026, 1, 1), date(2026, 6, 30)), 2)

    def test_completar_la_orden_de_calibracion_actualiza_fechas_y_certificado_del_equipo(self):
        balanza = self.equipo('K3-BAL-01', ultima_calibracion=date(2025, 1, 10), proxima_calibracion=date(2026, 1, 10))
        hermana = self.equipo('K3-BAL-02', ultima_calibracion=date(2025, 1, 10), proxima_calibracion=date(2026, 1, 10))
        plan = PlanMantenimientoEquipo.objects.create(equipo=balanza, nombre='Calibración anual ficticia',
                                                      tipo='calibracion', frecuencia_dias=365,
                                                      proxima_ejecucion=date(2026, 3, 1))
        orden = self.completar_calibracion(balanza, date(2026, 3, 2), plan=plan)
        self.assertEqual((balanza.ultima_calibracion, balanza.proxima_calibracion),
                         (date(2026, 3, 2), date(2026, 3, 2) + timedelta(days=365)))
        self.assertTrue(balanza.certificado_calibracion.name.startswith(f'equipos/calibraciones/K3-BAL-01-{orden.codigo}'))
        with balanza.certificado_calibracion.open('rb') as certificado:
            self.assertEqual(certificado.read(), b'%PDF-1.4 certificado ficticio K3')
        hermana.refresh_from_db()
        self.assertEqual((hermana.ultima_calibracion, hermana.certificado_calibracion.name), (date(2025, 1, 10), ''))
        evento = EventoCicloVidaEquipo.objects.get(mantenimiento=orden, tipo='calibracion')
        self.assertIn('con certificado', evento.descripcion)
        auditoria = RegistroAuditoriaUnidad.objects.get(unidad=self.unidad, entidad='recursos.UnidadEquipo',
                                                        objeto_id=str(balanza.pk))
        self.assertEqual(auditoria.usuario, self.responsable)
        self.assertIn(orden.codigo, auditoria.descripcion)
        fila = reporte_calibracion(self.unidad, date(2026, 1, 1), date(2026, 6, 30))['rows'][0]
        self.assertEqual(fila[1:3], ['02/03/2026', '02/03/2027'])
        self.assertTrue(fila[5].startswith('Certificado: K3-BAL-01-'))

    def test_sin_plan_de_calibracion_la_proxima_queda_como_estaba(self):
        balanza = self.equipo('K3-BAL-01', ultima_calibracion=date(2025, 6, 1), proxima_calibracion=date(2026, 6, 1))
        vieja = self.equipo('K3-BAL-02', ultima_calibracion=date(2024, 6, 1), proxima_calibracion=date(2025, 6, 1))
        self.completar_calibracion(balanza, date(2026, 3, 2))
        self.completar_calibracion(vieja, date(2026, 3, 2))
        self.assertEqual((balanza.ultima_calibracion, balanza.proxima_calibracion), (date(2026, 3, 2), date(2026, 6, 1)))
        # Una próxima que ya quedó atrás no se presenta como vigente: queda sin programar.
        self.assertEqual((vieja.ultima_calibracion, vieja.proxima_calibracion), (date(2026, 3, 2), None))

    def test_la_migracion_copia_las_fechas_del_modelo_a_sus_equipos(self):
        primera, segunda = self.equipo('K3-BAL-01'), self.equipo('K3-BAL-02')
        sin_fechas = UnidadEquipo.objects.create(
            codigo_unidad='K3-MESA-01', laboratorio=self.unidad,
            equipo=EquiposServicios.objects.create(nombre='Mesa ficticia K3', codigo='MOD-K3-MESA'))
        EquiposServicios.objects.filter(pk=self.modelo.pk).update(
            fecha_ultima_calibracion=date(2025, 9, 1), proxima_calibracion=date(2026, 9, 1))
        CALIBRACION.fechas_del_modelo_a_sus_equipos(registro_de_apps, None)
        for equipo in (primera, segunda):
            equipo.refresh_from_db()
            self.assertEqual((equipo.ultima_calibracion, equipo.proxima_calibracion, equipo.certificado_calibracion.name),
                             (date(2025, 9, 1), date(2026, 9, 1), ''))
        sin_fechas.refresh_from_db()
        self.assertEqual((sin_fechas.ultima_calibracion, sin_fechas.proxima_calibracion), (None, None))
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.fecha_ultima_calibracion, date(2025, 9, 1))
