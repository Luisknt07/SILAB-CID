from io import StringIO

from django.contrib import admin
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.recursos.models.equipos import EquiposServicios
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad


@override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
class ConfiguracionServiciosFablabTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Manufactura Digital y Prototipado',
            descripcion='Unidad de prueba para configurar servicios FabLab.',
            fecha_inicio='2026-01-01',
            dependencia='laboratorios',
            slug='laboratorio-fabricacion-digital-prototipado',
        )

    def test_modalidades_nuevas_son_compatibles_con_servicios_existentes(self):
        servicio = FablabService.objects.create(
            code='SERVICIO-BASE',
            nombre='Servicio existente',
            unidad=self.unidad,
        )

        self.assertTrue(servicio.permite_modelo_listo)
        self.assertTrue(servicio.permite_diseno_asistido)
        self.assertTrue(servicio.permite_diseno_completo)
        self.assertEqual(servicio.resultado_entregado, '')
        self.assertEqual(servicio.tutorial_youtube_url, '')

    def test_admin_expone_detalle_y_modalidades_sin_tutorial_por_servicio(self):
        registro = admin.site._registry[FablabService]
        campos = {
            campo
            for _titulo, opciones in registro.fieldsets
            for campo in opciones['fields']
        }

        self.assertTrue({
            'imagen_referencial',
            'imagen_catalogo',
            'vista_previa_imagen',
            'resultado_entregado',
            'cuando_elegirlo',
            'tiempo_estimado_texto',
            'permite_modelo_listo',
            'permite_diseno_asistido',
            'permite_diseno_completo',
        }.issubset(campos))
        self.assertNotIn('tutorial_titulo', campos)
        self.assertNotIn('tutorial_youtube_url', campos)

    def test_comando_carga_cinco_servicios_detallados_y_es_idempotente(self):
        salida = StringIO()
        opciones = {
            'unidad': self.unidad.slug,
            'confirmar_datos_demo': True,
            'stdout': salida,
        }
        call_command('cargar_pruebas_fablab', **opciones)
        call_command('cargar_pruebas_fablab', **opciones)

        servicios = FablabService.objects.filter(unidad=self.unidad)
        self.assertEqual(servicios.count(), 5)
        for servicio in servicios:
            with self.subTest(servicio=servicio.code):
                self.assertTrue(servicio.resultado_entregado)
                self.assertTrue(servicio.cuando_elegirlo)
                self.assertTrue(servicio.tiempo_estimado_texto)
                self.assertTrue(servicio.imagen_catalogo)
                self.assertEqual(servicio.tutorial_titulo, '')
                self.assertEqual(servicio.tutorial_youtube_url, '')

        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)
        self.assertEqual(configuracion.tutorial_recursos_url, '')
        self.assertEqual(configuracion.tutorial_servicios_url, '')

        # El catalogo agrupa por familia: ambas impresoras 3D quedan juntas.
        self.assertEqual(servicios.get(code='FAB-SRV-FDM').familia_catalogo, 'Impresión 3D')
        self.assertEqual(servicios.get(code='FAB-SRV-SLA').familia_catalogo, 'Impresión 3D')
        self.assertEqual(servicios.get(code='FAB-SRV-SCAN').familia, 'Digitalización 3D')
        escaneo = servicios.get(code='FAB-SRV-SCAN')
        self.assertFalse(escaneo.permite_modelo_listo)
        self.assertTrue(escaneo.permite_diseno_asistido)
        self.assertTrue(escaneo.permite_diseno_completo)

        programas = SoftwareDisponible.objects.filter(unidad=self.unidad)
        self.assertEqual(programas.count(), 12)
        # Cada equipo que opera con un programa propio lo declara obligatorio;
        # la estacion CAD ofrece programas opcionales y admite instalar otros.
        self.assertEqual(programas.filter(uso_en_equipo='obligatorio').count(), 6)
        for programa in programas.filter(uso_en_equipo='obligatorio'):
            with self.subTest(programa=programa.codigo):
                self.assertTrue(programa.equipos_instalados.exists())
                self.assertFalse(programa.equipos_instalados.filter(equipo__codigo='FAB-EQ-CAD').exists())
        self.assertTrue(programas.filter(codigo='FAB-SW-FUSION', uso_en_equipo='opcional').exists())
        self.assertTrue(EquiposServicios.objects.get(codigo='FAB-EQ-CAD').admite_software_adicional)
        self.assertFalse(EquiposServicios.objects.get(codigo='FAB-EQ-FDM').admite_software_adicional)
        for programa in programas:
            with self.subTest(programa=programa.codigo):
                # El software de uso general (acceso por red) no exige equipo.
                if programa.tipo_acceso != 'red':
                    self.assertTrue(programa.equipos_instalados.exists())
                self.assertTrue(programa.logo_publico_url.startswith('/static/img/software/'))
