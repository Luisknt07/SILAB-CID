"""La pestaña «Ubicación»: el punto exacto de la unidad sobre el mapa de las sedes.

El responsable marca el punto en el editor de la unidad; la ficha lo muestra
con la etiqueta completa de su dirección, las sedes de la UPEC resaltadas y
sus edificios, dibujados a mano en el editor de sedes (los de la matriz
parten de OpenStreetMap). Cada sede se ubica en su propio editor. Las unidades
de un mismo edificio comparten marcador, se ordenan por piso y se reconocen
por la miniatura de su imagen.
"""
import tempfile
from datetime import date
from decimal import Decimal
from importlib import import_module
from io import BytesIO

from tests.historia import registro_anterior

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.directorio_unidades.presentation.ubicacion import datos_mapa, en_el_mismo_punto, miniatura, sedes_en_el_mapa
from apps.directorio_unidades.models.sedes import SedeInstitucional
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce

DIRECCION_CAMPUS = 'Calle Antisana y Av. Universitaria, Tulcán 040102, Carchi, Ecuador'


class ElPuntoDeLaUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Realidad Extendida', slug='laboratorio-realidad-extendida-mapa',
            dependencia='laboratorios', ubicacion='Edificio Aulas 3', direccion=DIRECCION_CAMPUS,
            fecha_inicio=date(2026, 1, 1),
        )

    def mapa(self):
        return self.client.get(reverse('ubicacion_unidad', args=[self.unidad.slug]))

    def marcar(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(latitud=Decimal('0.804396'), longitud=Decimal('-77.734790'))

    def test_latitud_y_longitud_van_juntas(self):
        sola = Unidad(nombre='Unidad a medias', latitud=Decimal('0.8'))
        with self.assertRaises(ValidationError) as error:
            sola.clean()
        self.assertIn('longitud', error.exception.message_dict)
        Unidad(nombre='Unidad completa', latitud=Decimal('0.8'), longitud=Decimal('-77.7')).clean()
        Unidad(nombre='Unidad sin punto').clean()

    def test_la_etiqueta_une_el_espacio_y_la_direccion(self):
        self.assertEqual(self.unidad.direccion_completa, f'Edificio Aulas 3 · {DIRECCION_CAMPUS}')
        self.assertEqual(Unidad(nombre='Sin datos').direccion_completa, '')

    def test_sin_punto_muestra_el_campus_y_lo_dice(self):
        respuesta = self.mapa()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
        self.assertIsNone(respuesta.context['mapa']['punto'])
        self.assertContains(respuesta, 'Punto exacto por marcar')
        self.assertIn('maps/search/', respuesta.context['mapa']['comoLlegar'])
        # El público no recibe el acceso al editor.
        self.assertNotContains(respuesta, 'Marcarlo en el editor')

    def test_con_punto_lleva_la_etiqueta_completa_y_la_ruta(self):
        self.marcar()
        respuesta = self.mapa()
        mapa = respuesta.context['mapa']
        self.assertEqual(mapa['punto'], [0.804396, -77.73479])
        self.assertEqual(mapa['espacio'], 'Edificio Aulas 3')
        self.assertEqual(mapa['direccion'], DIRECCION_CAMPUS)
        self.assertIn('maps/dir/', mapa['comoLlegar'])
        self.assertIn('destination=0.804396%2C-77.734790', mapa['comoLlegar'])
        self.assertContains(respuesta, 'id="datosMapaUnidad"')
        self.assertContains(respuesta, 'data-mapa-ver="unidad"')
        self.assertNotContains(respuesta, 'Punto exacto por marcar')

    def test_una_unidad_inactiva_no_tiene_mapa(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(activo=False)
        self.assertEqual(self.mapa().status_code, 404)


class LasUnidadesDeUnMismoPuntoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def unidad(slug, latitud, longitud, piso):
            return Unidad.objects.create(
                nombre=f'Laboratorio {slug}', slug=f'laboratorio-{slug}', dependencia='laboratorios',
                ubicacion='Edificio Aulas 3', direccion=DIRECCION_CAMPUS, piso=piso, fecha_inicio=date(2026, 1, 1),
                latitud=Decimal(latitud), longitud=Decimal(longitud),
            )
        cls.primero = unidad('primero', '0.804396', '-77.734790', 1)
        # Unos 5 m al norte: el mismo edificio, un piso más arriba.
        cls.segundo = unidad('segundo', '0.804441', '-77.734790', 2)
        # Unos 50 m al este: otro edificio.
        cls.lejos = unidad('lejos', '0.804396', '-77.734340', 2)

    def test_el_piso_se_lee_en_la_etiqueta(self):
        self.assertEqual([Unidad(piso=piso).piso_texto for piso in (None, 0, 3, -1)], ['', 'Planta baja', 'Piso 3', 'Subsuelo 1'])
        self.assertEqual(self.segundo.espacio_completo, 'Edificio Aulas 3 · Piso 2')
        self.assertEqual(self.segundo.direccion_completa, f'Edificio Aulas 3 · Piso 2 · {DIRECCION_CAMPUS}')

    def test_las_del_mismo_edificio_comparten_marcador_por_piso(self):
        juntas = en_el_mismo_punto(self.segundo)
        self.assertEqual([(unidad['nombre'], unidad['piso'], unidad['actual']) for unidad in juntas], [
            ('Laboratorio primero', 'Piso 1', False), ('Laboratorio segundo', 'Piso 2', True),
        ])
        self.assertEqual(juntas[0]['url'], self.primero.get_absolute_url())
        self.assertEqual(datos_mapa(self.lejos)['enElMismoPunto'][0]['nombre'], 'Laboratorio lejos')
        self.assertEqual(len(datos_mapa(self.lejos)['enElMismoPunto']), 1)
        self.assertEqual(en_el_mismo_punto(Unidad(nombre='Sin punto')), [])

    def test_la_miniatura_se_recorta_una_vez_y_cambia_con_la_imagen(self):
        with tempfile.TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            self.assertEqual(miniatura(self.primero), '')
            contenido = BytesIO()
            Image.new('RGB', (320, 200), (30, 110, 70)).save(contenido, 'PNG')
            self.primero.imagen = SimpleUploadedFile('portada.png', contenido.getvalue(), content_type='image/png')
            self.primero.save()
            url = miniatura(self.primero)
            from urllib.parse import urlsplit, parse_qs
            partes = urlsplit(url)
            self.assertTrue(partes.path.endswith('.jpg'))
            self.assertTrue(parse_qs(partes.query))
            nombre = partes.path.split('/media/', 1)[1]
            with default_storage.open(nombre) as archivo, Image.open(archivo) as recorte:
                self.assertEqual(recorte.size, (96, 96))
            self.assertEqual(miniatura(self.primero), url)
            self.assertEqual(datos_mapa(self.primero)['imagen'], url)

    def test_el_editor_ofrece_el_piso_y_las_demas_unidades(self):
        self.client.force_login(get_user_model().objects.create_superuser('super.piso', 'sp@upec.edu.ec', 'Clave-segura-2026'))
        editor = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.primero.pk]))
        self.assertContains(editor, 'name="piso"')
        self.assertContains(editor, 'data-unidades="')
        self.assertContains(editor, 'Laboratorio segundo')
        # El editor de sedes no carga las unidades.
        sede = SedeInstitucional.objects.create(nombre='Sede de prueba del editor')
        self.assertContains(self.client.get(reverse('admin:directorio_unidades_sedeinstitucional_change', args=[sede.pk])),
                            'data-unidades="[]"')


class LasSedesEnElMapaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # La migración siembra las sedes reales; aquí se miden solo las de la prueba.
        SedeInstitucional.objects.all().delete()
        cls.matriz = SedeInstitucional.objects.create(
            nombre='Sede matriz', localidad='Tulcán', direccion=DIRECCION_CAMPUS,
            latitud=Decimal('0.805253'), longitud=Decimal('-77.734336'), orden=1,
        )
        cls.sin_punto = SedeInstitucional.objects.create(nombre='Sede Norte', localidad='Tulcán', orden=2)
        cls.cerrada = SedeInstitucional.objects.create(
            nombre='Sede cerrada', latitud=Decimal('0.7'), longitud=Decimal('-77.7'), orden=3, activa=False,
        )

    def test_van_todas_las_activas_por_separado(self):
        sedes = sedes_en_el_mapa()
        # La que aún no tiene punto también va: el selector la muestra por ubicar.
        self.assertEqual([sede['nombre'] for sede in sedes], ['Sede matriz', 'Sede Norte'])
        matriz, norte = sedes
        self.assertEqual(matriz['punto'], [0.805253, -77.734336])
        self.assertEqual(matriz['localidad'], 'Tulcán')
        self.assertIn('destination=0.805253%2C-77.734336', matriz['comoLlegar'])
        self.assertEqual((norte['punto'], norte['comoLlegar'], norte['edificios']), (None, '', []))
        # En su propio editor la sede es el marcador, no un distintivo más.
        self.assertEqual([sede['nombre'] for sede in sedes_en_el_mapa(excluir=self.matriz.pk)], ['Sede Norte'])

    def test_la_sede_tambien_pide_latitud_y_longitud_juntas(self):
        with self.assertRaises(ValidationError) as error:
            SedeInstitucional(nombre='Campus a medias', longitud=Decimal('-78.1')).clean()
        self.assertIn('latitud', error.exception.message_dict)

    def test_las_figuras_necesitan_tres_vertices_y_los_edificios_nombre(self):
        cuadro = [[0.8155, -77.7100], [0.8157, -77.7100], [0.8157, -77.7096], [0.8155, -77.7096]]
        SedeInstitucional(nombre='Bien dibujada', contorno=cuadro, edificios=[{'nombre': 'Bloque A', 'contorno': cuadro}]).clean()
        for contorno, edificios in (
            ([[0.8155, -77.71], [0.8157, -77.71]], []),
            ([], [{'nombre': '', 'contorno': cuadro}]),
            ([], [{'nombre': 'Bloque B', 'contorno': [[0.8155, 'x'], [0.8157, -77.71], [0.8157, -77.70]]}]),
            ([], [{'nombre': 'Bloque C', 'contorno': [[95, -77.71], [0.8157, -77.71], [0.8157, -77.70]]}]),
        ):
            with self.assertRaises(ValidationError):
                SedeInstitucional(nombre='Mal dibujada', contorno=contorno, edificios=edificios).clean()

    def test_la_ficha_recibe_las_sedes(self):
        unidad = Unidad.objects.create(nombre='Planta de prueba', slug='planta-prueba-sedes', dependencia='plantas_piloto',
                                       fecha_inicio=date(2026, 1, 1))
        respuesta = self.client.get(reverse('ubicacion_unidad', args=[unidad.slug]))
        self.assertEqual([sede['nombre'] for sede in respuesta.context['mapa']['sedes']], ['Sede matriz', 'Sede Norte'])
        self.assertContains(respuesta, 'Mientras tanto se muestran las sedes de la')

    def test_el_editor_de_sedes_marca_el_punto_y_dibuja(self):
        self.client.force_login(get_user_model().objects.create_superuser('super.sedes', 'ss@upec.edu.ec', 'Clave-segura-2026'))
        lista = self.client.get(reverse('admin:directorio_unidades_sedeinstitucional_changelist'))
        self.assertContains(lista, 'Sede Norte')
        url = reverse('admin:directorio_unidades_sedeinstitucional_change', args=[self.sin_punto.pk])
        editor = self.client.get(url)
        for fragmento in ('data-mapa-editor data-dibujo', 'name="latitud"', 'name="longitud"', 'name="localidad"',
                          'type="hidden" name="contorno"', 'type="hidden" name="edificios"',
                          'portal/js/pages/unidades/mapa_unidad.js', 'portal/js/pages/unidades/dibujo_sede.js'):
            self.assertContains(editor, fragmento)
        self.assertContains(editor, 'Sede matriz')
        cuadro = [[0.8155, -77.71], [0.8157, -77.71], [0.8157, -77.7096], [0.8155, -77.7096]]
        respuesta = self.client.post(url, {
            'nombre': 'Sede Norte', 'localidad': 'Tulcán', 'direccion': '', 'latitud': '0.815534', 'longitud': '-77.709853',
            'contorno': '[]', 'edificios': f'[{{"nombre": "Bloque administrativo", "contorno": {cuadro}}}]',
            'orden': '2', 'activa': 'on',
        })
        self.assertEqual(respuesta.status_code, 302)
        self.sin_punto.refresh_from_db()
        self.assertEqual(self.sin_punto.punto, [0.815534, -77.709853])
        self.assertEqual(self.sin_punto.edificios, [{'nombre': 'Bloque administrativo', 'contorno': cuadro}])
        self.assertEqual(self.sin_punto.contorno, [])


class LaSiembraDeLasSedesTests(TestCase):
    """La migración dibuja la matriz y ubica las sedes sin pisar lo ya editado."""

    def sembrar(self):
        import_module('apps.historial_modelos.migrations.0255_dibujo_de_sedes').dibujar_sedes(registro_anterior(), None)

    def test_dibuja_la_matriz_y_ubica_las_demas(self):
        SedeInstitucional.objects.all().delete()
        SedeInstitucional.objects.create(nombre='Sede matriz', orden=1)
        SedeInstitucional.objects.create(nombre='Campus Cayambe', orden=7)
        SedeInstitucional.objects.create(nombre='Centro Experimental Alonso Tadeo', latitud=Decimal('0.601389'),
                                         longitud=Decimal('-78.130833'), orden=6)
        self.sembrar()
        matriz = SedeInstitucional.objects.get(nombre='Sede matriz')
        self.assertGreaterEqual(len(matriz.contorno), 3)
        nombres = [edificio['nombre'] for edificio in matriz.edificios]
        for nombre in ('Central UPEC', 'Edificio Aulas 1', 'Edificio Aulas 4', 'Edificio de Posgrados', 'Laboratorios UPEC'):
            self.assertIn(nombre, nombres)
        matriz.full_clean()
        self.assertEqual(SedeInstitucional.objects.get(nombre='Campus Cayambe').punto, [-0.004559, -78.177842])
        # El punto entregado por la universidad reemplaza la coordenada publicada.
        self.assertEqual(SedeInstitucional.objects.get(nombre='Centro Experimental Alonso Tadeo').punto, [0.605984, -78.12651])

    def test_no_pisa_lo_editado_a_mano(self):
        SedeInstitucional.objects.all().delete()
        propio = [[0.8, -77.7], [0.81, -77.7], [0.81, -77.71]]
        SedeInstitucional.objects.create(nombre='Sede matriz', edificios=[{'nombre': 'Propio', 'contorno': propio}])
        SedeInstitucional.objects.create(nombre='Sede Sur', latitud=Decimal('0.79'), longitud=Decimal('-77.74'))
        self.sembrar()
        self.assertEqual(SedeInstitucional.objects.get(nombre='Sede matriz').edificios, [{'nombre': 'Propio', 'contorno': propio}])
        self.assertEqual(SedeInstitucional.objects.get(nombre='Sede Sur').punto, [0.79, -77.74])


class LaUbicacionEnLaFichaYElEditorTests(BasePlantaProduce):
    def test_la_unidad_de_la_planta_abre_el_mapa(self):
        url = reverse('ubicacion_unidad', args=[self.unidad.slug])
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'data-id="ubicacion-unidad"')
        self.assertContains(ficha, f'data-ui-click="abrirUbicacion" data-ui-arg0="{url}"')
        # Sin punto, el panel de información no ofrece un mapa vacío.
        self.assertNotContains(ficha, 'class="unit-map-link"')
        Unidad.objects.filter(pk=self.unidad.pk).update(latitud=Decimal('0.805000'), longitud=Decimal('-77.734000'))
        self.assertContains(self.client.get(self.unidad.get_absolute_url()), 'class="unit-map-link"')

    def test_la_coordinacion_llega_al_editor_desde_el_mapa(self):
        self.client.force_login(self.coordinacion)
        respuesta = self.client.get(reverse('ubicacion_unidad', args=[self.unidad.slug]))
        editor = reverse('admin:directorio_unidades_unidad_change', args=[self.unidad.pk])
        self.assertEqual(respuesta.context['editar_url'], editor)
        self.assertContains(respuesta, 'Marcarlo en el editor')

    def test_el_editor_marca_el_punto_en_el_mapa(self):
        superusuario = get_user_model().objects.create_superuser('super.mapa', 'sm@upec.edu.ec', 'Clave-segura-2026')
        for usuario in (self.coordinacion, superusuario):
            self.client.force_login(usuario)
            editor = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.unidad.pk]))
            self.assertEqual(editor.status_code, 200)
            for fragmento in ('data-mapa-editor', 'name="latitud"', 'name="longitud"', 'name="direccion"',
                              'js/vendor/leaflet/leaflet.js', 'portal/js/pages/unidades/mapa_unidad.js'):
                self.assertContains(editor, fragmento)
