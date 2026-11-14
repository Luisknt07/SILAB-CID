"""Qué es cada cosa en una unidad, y cómo lo cuentan el asistente y el panel.

Un equipo principal se reserva; un auxiliar acompaña a un principal y no se
reserva aparte. El inventario distingue insumos, reactivos, materiales,
empaque, protección y limpieza, con la misma definición en un taller, un
laboratorio húmedo y una planta piloto.
"""

from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios
from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class TaxonomiaDeRecursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Biotecnología Aplicada',
            descripcion='Unidad de prueba.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-microbiologia-biotecnologia-aplicada',
        )
        call_command('cargar_laboratorios_institucionales', laboratorio='biotecnologia')
        Usuario = get_user_model()
        cls.coordinacion = Usuario.objects.create_user(
            username='coordinacion.bio', email='coordinacion.bio@upec.edu.ec', password='Clave-2026'
        )
        identificar(cls.coordinacion, tipo_usuario='administrativo')
        ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.coordinacion, nombre='Coordinación',
            rol='coordinacion', email='coordinacion.bio@upec.edu.ec', recibe_reservas=True,
        )

    # ------------------------------------------------------------- equipos
    def test_un_auxiliar_acompana_al_principal_y_no_se_reserva_aparte(self):
        balanza = EquiposServicios.objects.get(codigo='BIO-EQ-BALANZA')
        termociclador = EquiposServicios.objects.get(codigo='BIO-EQ-TERMOCICLADOR')
        self.assertEqual(balanza.rol, 'auxiliar')
        self.assertTrue(balanza.es_auxiliar)
        self.assertIn(termociclador, balanza.apoya_a.all())
        self.assertIn(balanza, termociclador.auxiliares.all())

        respuesta = self.client.get(reverse('obtener_unidades_laboratorio', args=[self.unidad.pk]))
        unidades = {item['codigo']: item for item in respuesta.json()['unidades']}
        # La balanza no es una tarjeta más del asistente.
        self.assertNotIn('BIO-UNIT-BAL-01', unidades)
        self.assertNotIn('BIO-UNIT-PH-01', unidades)
        # Pero el termociclador cuenta con ella.
        pcr = unidades['BIO-UNIT-PCR-01']
        self.assertEqual(pcr['rol'], 'principal')
        self.assertIn('Balanza analítica', pcr['auxiliares'])
        # Y la categoría es la que declaró la unidad, no una palabra clave.
        self.assertEqual(pcr['categoria'], 'Biología molecular')

    def test_la_categoria_por_palabra_clave_sigue_cuando_la_unidad_no_clasifica(self):
        sin_categoria = EquiposServicios.objects.create(
            codigo='TEST-IMPRESORA', nombre='Impresora 3D de prueba', descripcion='',
        )
        UnidadEquipo.objects.create(
            codigo_unidad='TEST-UNIT-IMP', equipo=sin_categoria, laboratorio=self.unidad,
        )
        respuesta = self.client.get(reverse('obtener_unidades_laboratorio', args=[self.unidad.pk]))
        unidades = {item['codigo']: item for item in respuesta.json()['unidades']}
        self.assertEqual(unidades['TEST-UNIT-IMP']['categoria'], 'Impresión 3D')

    def test_el_panel_declara_el_rol_y_a_quien_apoya(self):
        self.client.force_login(self.coordinacion)
        principal = EquiposServicios.objects.get(codigo='BIO-EQ-CENTRIFUGA')
        respuesta = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'recursos',
                'entidad': 'equipo',
                'codigo_catalogo': 'BIO-EQ-VORTEX',
                'nombre_catalogo': 'Agitador vórtex',
                'rol_equipo': 'auxiliar',
                'apoya_a': [str(principal.pk)],
                'codigo_unidad': 'BIO-UNIT-VOR-01',
                'estado_unidad': 'disponible',
                'ubicacion_especifica': 'Área de biología molecular',
                'activa': 'on',
            },
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        vortex = EquiposServicios.objects.get(codigo='BIO-EQ-VORTEX')
        self.assertEqual(vortex.rol, 'auxiliar')
        self.assertEqual(list(vortex.apoya_a.all()), [principal])
        # Un auxiliar no puede apoyar a otro auxiliar.
        balanza = EquiposServicios.objects.get(codigo='BIO-EQ-BALANZA')
        respuesta = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'recursos',
                'entidad': 'equipo',
                'registro_id': str(UnidadEquipo.objects.get(codigo_unidad='BIO-UNIT-VOR-01').pk),
                'equipo_catalogo_id': str(vortex.pk),
                'rol_equipo': 'auxiliar',
                'apoya_a': [str(balanza.pk)],
                'codigo_unidad': 'BIO-UNIT-VOR-01',
                'estado_unidad': 'disponible',
                'activa': 'on',
            },
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('principales', respuesta.json()['error'])

    def test_una_planta_puede_compartir_unidades_de_equipo(self):
        planta = Unidad.objects.create(
            nombre='Planta piloto de prueba', descripcion='Comparte equipos.',
            fecha_inicio=date(2026, 1, 1), dependencia='plantas_piloto', slug='planta-prueba',
        )
        unidad_equipo = UnidadEquipo.objects.get(codigo_unidad='BIO-UNIT-AUT-01')
        unidad_equipo.laboratorios.add(planta)
        unidad_equipo.full_clean()
        self.assertIn(planta, unidad_equipo.laboratorios.all())

    # ---------------------------------------------------------- inventario
    def test_el_inventario_distingue_siete_clases_y_las_muestra(self):
        claves = [codigo for codigo, _ in Consumible.CLASIFICACIONES]
        self.assertEqual(
            claves,
            ['insumo', 'reactivo', 'material', 'empaque', 'proteccion', 'limpieza', 'otro'],
        )
        self.assertEqual(set(Consumible.CLASIFICACION_DETALLE), set(claves))
        self.assertEqual(Consumible.objects.get(codigo='BIO-REA-AGAROSA').clasificacion, 'reactivo')
        self.assertEqual(Consumible.objects.get(codigo='BIO-MAT-GUANTES').clasificacion, 'proteccion')
        self.assertEqual(Consumible.objects.get(codigo='BIO-MAT-PUNTAS').clasificacion, 'material')

        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(pagina, 'data-inventory-type="reactivo"')
        self.assertContains(pagina, 'data-inventory-type="proteccion"')
        self.assertContains(pagina, 'Reactivos')
        self.assertContains(pagina, 'Protección')

    def test_el_panel_ofrece_las_clases_y_guarda_un_reactivo(self):
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
                                {'view': 'recursos', 'modo_recursos': 'insumos'})
        self.assertContains(panel, '<option value="reactivo">Reactivo</option>')
        self.assertContains(panel, '<option value="empaque">Empaque</option>')
        respuesta = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'consumible',
                'codigo': 'BIO-REA-TAQ',
                'nombre': 'Polimerasa Taq',
                'clasificacion': 'reactivo',
                'familia': 'Reactivos de PCR',
                'presentacion': 'Vial de 500 unidades',
                'cantidad_por_presentacion': '500',
                'unidad_medida': 'unidad',
                'stock_total': '0',
                'minimo': '100',
                'stock_seguridad': '50',
                'stock_objetivo': '500',
                'precio_unitario': '0.35',
                'activo': 'on',
                'visible_en_reservas': 'on',
            },
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(Consumible.objects.get(codigo='BIO-REA-TAQ').clasificacion, 'reactivo')
        rechazo = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'consumible',
                'codigo': 'BIO-X',
                'nombre': 'Clase inválida',
                'clasificacion': 'herramienta',
                'unidad_medida': 'unidad',
                'stock_total': '0',
                'minimo': '0',
            },
        )
        self.assertEqual(rechazo.status_code, 400)


@override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
class TaxonomiaDelFabLabTests(TestCase):
    """El ejemplo con el que se explicó la regla: la impresora, su secador,
    el filamento y las espátulas."""

    SLUG = 'laboratorio-fabricacion-digital-prototipado'

    @classmethod
    def setUpTestData(cls):
        administrador = get_user_model().objects.create_superuser(
            username='admin-taxonomia', email='admin.taxonomia@upec.edu.ec', password='Clave-2026'
        )
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Manufactura Digital y Prototipado',
            descripcion='El FabLab, con su secador y su filamento.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug=cls.SLUG,
            administrador=administrador,
        )
        call_command(
            'cargar_pruebas_fablab',
            unidad=cls.SLUG,
            confirmar_datos_demo=True,
            stdout=StringIO(),
        )

    def test_la_impresora_es_principal_y_el_secador_la_acompana(self):
        fdm = EquiposServicios.objects.get(codigo='FAB-EQ-FDM')
        secador = EquiposServicios.objects.get(codigo='FAB-EQ-SECADOR')
        self.assertEqual(fdm.rol, 'principal')
        self.assertEqual(secador.rol, 'auxiliar')
        self.assertEqual(list(secador.apoya_a.all()), [fdm])
        self.assertTrue(CategoriaEquipo.objects.filter(codigo='EQ-APOYO').exists())

        respuesta = self.client.get(reverse('obtener_unidades_laboratorio', args=[self.unidad.pk]))
        unidades = {item['codigo']: item for item in respuesta.json()['unidades']}
        self.assertNotIn('UE-FAB-SEC-01', unidades)
        impresoras = [item for item in unidades.values() if item['equipo_codigo'] == 'FAB-EQ-FDM']
        self.assertTrue(impresoras)
        self.assertEqual(impresoras[0]['auxiliares'], ['Secador de filamento'])

    def test_el_filamento_es_insumo_y_lo_que_se_desgasta_es_material(self):
        clases = {
            'FAB-MAT-PLA': 'insumo',        # se convierte en la pieza
            'FAB-MAT-MDF3': 'insumo',       # la lámina también
            'FAB-CON-FRESA': 'material',    # se desgasta, no es parte de la pieza
            'FAB-CON-FEP': 'material',
            'FAB-CON-IPA': 'reactivo',      # sustancia química del posprocesado
            'FAB-CON-GUANTES': 'proteccion',
        }
        for codigo, clase in clases.items():
            with self.subTest(codigo=codigo):
                self.assertEqual(Consumible.objects.get(codigo=codigo).clasificacion, clase)
