"""Catálogo compartido de dimensiones y métricas de uso.

Antes existían dos reportes con definiciones propias: el de la unidad medía
horas y asistencia desde la ejecución real y el institucional sumaba la
duración planificada. Estas pruebas fijan una sola definición y comprueban que
las dos pantallas la usen.
"""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.reportes_dimensiones import agrupar, dimensiones_de, es_multiple, horas_efectivas, participantes
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad


class MetricasCompartidasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de metricas',
            slug='laboratorio-metricas',
            dependencia='laboratorios',
            descripcion='Unidad para validar el catalogo de reportes.',
            fecha_inicio=date(2026, 1, 1),
        )
        cls.usuario = get_user_model().objects.create_user(
            'usuario-metricas', password='clave-segura'
        )

    def _reserva(self, **extra):
        datos = {
            'laboratorio': self.unidad,
            'usuario': self.usuario,
            'fecha': date(2026, 10, 6),
            'hora_inicio': time(9),
            'hora_fin': time(11),
            'equipo_codigo': 'EQ-MET',
            'equipo_nombre': 'Equipo de metricas',
            'numero_participantes': 4,
        }
        datos.update(extra)
        return Reserva.objects.create(**datos)

    def test_una_reserva_sin_ejecucion_usa_su_horario_solicitado(self):
        reserva = self._reserva()

        self.assertEqual(horas_efectivas(reserva), 2.0)
        self.assertEqual(participantes(reserva), 4)

    def test_una_atencion_cerrada_usa_el_horario_y_la_asistencia_reales(self):
        reserva = self._reserva(
            estado='completada',
            resultado_cierre='atendida',
            detalle_ejecucion={
                'registrada_en': '2026-10-06T12:00:00Z',
                'horario_real': {'inicio': '09:15', 'fin': '10:45'},
                'asistentes_total': 3,
            },
        )

        self.assertTrue(reserva.es_efectiva)
        self.assertEqual(horas_efectivas(reserva), 1.5)
        self.assertEqual(participantes(reserva), 3)

    def test_solo_las_atenciones_efectivas_aportan_horas_y_asistencia(self):
        self._reserva(estado='pendiente')
        self._reserva(
            estado='completada',
            resultado_cierre='atendida',
            detalle_ejecucion={
                'registrada_en': '2026-10-06T12:00:00Z',
                'asistentes_total': 5,
            },
        )

        filas = agrupar(list(Reserva.objects.all()), 'estado')
        por_etiqueta = {fila['label']: fila for fila in filas}

        self.assertEqual(por_etiqueta['Pendiente']['total'], 1)
        self.assertEqual(por_etiqueta['Pendiente']['effective'], 0)
        self.assertEqual(por_etiqueta['Pendiente']['hours'], 0)
        self.assertEqual(por_etiqueta['Completada']['effective'], 1)
        self.assertEqual(por_etiqueta['Completada']['hours'], 2.0)
        self.assertEqual(por_etiqueta['Completada']['participants'], 5)


class DimensionRecursoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio combinado',
            slug='laboratorio-combinado',
            dependencia='laboratorios',
            descripcion='Unidad para validar recursos combinados.',
            fecha_inicio=date(2026, 1, 1),
        )
        cls.usuario = get_user_model().objects.create_user(
            'usuario-recursos', password='clave-segura'
        )

    def test_una_solicitud_combinada_cuenta_en_cada_recurso(self):
        espacio = EspacioReservable.objects.create(
            unidad=self.unidad, codigo='AREA-1', nombre='Área de impresión'
        )
        programa = SoftwareDisponible.objects.create(
            unidad=self.unidad, nombre='Fusion', version='2026', tipo_acceso='red'
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario,
            fecha=date(2026, 10, 7),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo='EQ-COMBI',
            equipo_nombre='Impresora FDM',
        )
        reserva.espacios_solicitados.add(espacio)
        reserva.software_solicitado.add(programa)

        filas = agrupar([reserva], 'recurso')
        etiquetas = {fila['label'] for fila in filas}

        self.assertIn('EQ-COMBI · Impresora FDM', etiquetas)
        self.assertIn('Área de impresión', etiquetas)
        self.assertIn('Fusion', etiquetas)
        self.assertTrue(
            es_multiple('recurso'),
            'la dimension debe declararse multiple para que el reporte lo advierta',
        )

    def test_las_dimensiones_de_una_sola_etiqueta_no_se_declaran_multiples(self):
        for clave, _etiqueta in dimensiones_de('unidad'):
            if clave != 'recurso':
                self.assertFalse(es_multiple(clave), clave)


class ReportesComparablesTests(TestCase):
    """Las dos pantallas deben ofrecer las mismas dimensiones y cifras."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_superuser(
            'staff-reportes', 'staff@upec.edu.ec', 'clave-segura'
        )
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio comparable',
            slug='laboratorio-comparable',
            dependencia='laboratorios',
            descripcion='Unidad para comparar ambos reportes.',
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.staff,
        )
        Reserva.objects.create(
            laboratorio=cls.unidad,
            usuario=cls.staff,
            fecha=date(2026, 10, 8),
            hora_inicio=time(9),
            hora_fin=time(12),
            equipo_codigo='EQ-CMP',
            equipo_nombre='Equipo comparable',
            estado='completada',
            resultado_cierre='atendida',
            facultad_beneficiaria='agropecuarias_ambientales',
            detalle_ejecucion={
                'registrada_en': '2026-10-08T13:00:00Z',
                'horario_real': {'inicio': '09:00', 'fin': '11:00'},
                'asistentes_total': 7,
            },
        )

    def test_el_reporte_de_la_unidad_ofrece_facultad_periodo_y_recurso(self):
        """Dimensiones que antes solo existían en el administrador."""
        claves = {clave for clave, _ in dimensiones_de('unidad')}

        self.assertLessEqual(
            {'facultad', 'periodo', 'semana_academica', 'recurso'}, claves
        )

    def test_ambos_reportes_informan_las_mismas_horas_efectivas(self):
        self.client.force_login(self.staff)

        panel = self.client.get(
            reverse('gestion_reporte_unidad', args=[self.unidad.slug]),
            {'categoria_reporte': 'reservas', 'agrupar': 'facultad',
             'desde': '2026-10-01', 'hasta': '2026-10-31'},
        )
        self.assertEqual(panel.status_code, 200)
        filas_panel = panel.context['reporte_gestion']['rows']
        self.assertEqual(len(filas_panel), 1)
        # 09:00 a 11:00 reales, no las 3 horas solicitadas.
        self.assertEqual(filas_panel[0]['hours'], 2.0)
        self.assertEqual(filas_panel[0]['participants'], 7)

        institucional = self.client.get(reverse('admin:reservas-reporte-uso'))
        self.assertEqual(institucional.status_code, 200)
        por_titulo = {
            reporte['titulo']: reporte
            for reporte in institucional.context['reportes']
        }
        fila_facultad = por_titulo['Uso por facultad beneficiaria']['filas'][0]

        self.assertEqual(fila_facultad['horas'], filas_panel[0]['hours'])
        self.assertEqual(fila_facultad['participantes'], filas_panel[0]['participants'])
