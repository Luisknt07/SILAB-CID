"""El listado de reservas se descarga como documento, no como fotografia.

El boton «Descargar» del admin llamaba a html2canvas: rasterizaba la pantalla
entera -barra lateral, menus y filtros incluidos- y pegaba la imagen en un PDF.
Salia borroso, cortado y con el logo como parte de la foto. Ahora el listado
pasa por el mismo presentador que los reportes de laboratorio, se ve antes de
bajarlo y se descarga con su cabecera, sus criterios y sus tablas.
"""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from config.identidad import configuracion_identidad

from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad


class ReporteDelListadoDeReservasTests(TestCase):
    def test_reporte_personalizado_comparte_identidad_html_pdf_y_nombre_neutral(self):
        producto, institucion = configuracion_identidad({
            'INSTITUTION_PROFILE': 'custom', 'INSTITUTION_NAME': 'Centro Regional',
            'INSTITUTION_CODE': 'CR', 'SYSTEM_SHORT_NAME': 'Laboratorios Regionales',
        })
        with override_settings(PRODUCT_IDENTITY=producto, INSTITUTION_IDENTITY=institucion):
            respuesta = self.client.get(self.url)
            self.assertContains(respuesta, 'Laboratorios Regionales · CR</title>')
            self.assertContains(respuesta, 'RES-REPORTE-1')
            self.assertContains(respuesta, 'Reportes e indicadores')
            self.assertContains(respuesta, 'data-ver-pdf')
            self.assertContains(respuesta, 'class="aula-pdf-modal"', count=1)
            pdf = self.client.get(self.url, {'formato': 'pdf'})
            self.assertIn(b'/Author (Centro Regional)', pdf.content)
            self.assertRegex(pdf['Content-Disposition'], r'filename="reservas-\d{8}-\d{4}\.pdf"')
            self.assertNotIn('upec', pdf['Content-Disposition'])

    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(
            username='admin-reporte-listado',
            email='reporte.listado@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.staff)
        self.unidad = Unidad.objects.create(
            nombre='Laboratorio del reporte',
            slug='laboratorio-del-reporte',
            dependencia='laboratorios',
            descripcion='Unidad para validar el reporte del listado.',
            fecha_inicio=date(2026, 1, 1),
        )
        self.otra = Unidad.objects.create(
            nombre='Laboratorio vecino',
            slug='laboratorio-vecino',
            dependencia='laboratorios',
            descripcion='Segunda unidad para contrastar el alcance.',
            fecha_inicio=date(2026, 1, 1),
        )
        self.reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.staff,
            codigo_reserva='RES-REPORTE-1',
            titulo_solicitud='Practica de titulacion',
            fecha=date(2026, 11, 3),
            hora_inicio=time(9),
            hora_fin=time(11),
            equipo_codigo='EQ-REP',
            equipo_nombre='Equipo del reporte',
            numero_participantes=12,
            estado='pendiente',
        )
        Reserva.objects.create(
            laboratorio=self.otra,
            usuario=self.staff,
            codigo_reserva='RES-REPORTE-2',
            titulo_solicitud='Analisis de muestras',
            fecha=date(2026, 11, 10),
            hora_inicio=time(14),
            hora_fin=time(16),
            equipo_codigo='EQ-VEC',
            equipo_nombre='Equipo vecino',
            numero_participantes=5,
            estado='confirmada',
        )

    @property
    def url(self):
        return reverse('admin:reservas-reporte-listado')

    def test_la_vista_previa_muestra_el_documento_con_logo_y_filas(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'logo_upec.png')
        self.assertContains(respuesta, 'Listado de solicitudes de reserva')
        self.assertContains(respuesta, 'ASÍ SE VA A DESCARGAR')
        self.assertContains(respuesta, 'RES-REPORTE-1')
        self.assertContains(respuesta, 'RES-REPORTE-2')
        # Dos unidades en la seleccion: el alcance lo dice, no lo inventa.
        self.assertContains(respuesta, '2 unidades académicas')
        self.assertContains(respuesta, 'Practica de titulacion')

    def test_la_vista_previa_lleva_a_la_descarga_y_de_vuelta_al_listado(self):
        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, 'formato=pdf')
        self.assertContains(respuesta, reverse('admin:reservas_reserva_changelist'))

    def test_el_pdf_es_un_documento_y_no_una_imagen_de_la_pantalla(self):
        respuesta = self.client.get(self.url, {'formato': 'pdf'})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta['Content-Disposition'].startswith('attachment;'))
        self.assertRegex(respuesta['Content-Disposition'], r'filename="reservas-\d{8}-\d{4}\.pdf"')
        contenido = respuesta.content
        self.assertTrue(contenido.startswith(b'%PDF'))
        # Una captura de pantalla viaja como una sola imagen; este PDF lleva el
        # texto de las solicitudes, asi que se puede buscar y copiar.
        self.assertIn(b'/Font', contenido)
        self.assertNotIn(b'/Image', contenido.split(b'/Font')[0][:400])

    def test_el_reporte_respeta_los_filtros_que_tenga_puesto_el_listado(self):
        respuesta = self.client.get(self.url, {'laboratorio__id__exact': self.unidad.pk})

        self.assertContains(respuesta, 'RES-REPORTE-1')
        self.assertNotContains(respuesta, 'RES-REPORTE-2')
        # El criterio aplicado queda escrito en la cabecera del documento.
        self.assertContains(respuesta, 'Laboratorio del reporte')
        self.assertContains(respuesta, 'CRITERIOS APLICADOS')

    def test_la_busqueda_del_listado_tambien_viaja_al_reporte(self):
        respuesta = self.client.get(self.url, {'q': 'Analisis de muestras'})

        self.assertContains(respuesta, 'RES-REPORTE-2')
        self.assertNotContains(respuesta, 'RES-REPORTE-1')
        self.assertContains(respuesta, 'Búsqueda')

    def test_un_filtro_inventado_devuelve_al_listado_en_vez_de_reventar(self):
        respuesta = self.client.get(self.url, {'campo_que_no_existe': '1'})

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.url, reverse('admin:reservas_reserva_changelist'))

    def test_el_reporte_esta_protegido_como_los_demas(self):
        self.client.logout()

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/admin/login/', respuesta.url)

    def test_el_listado_ofrece_el_reporte_y_ya_no_fotografia_la_pantalla(self):
        respuesta = self.client.get(reverse('admin:reservas_reserva_changelist'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.url)
        self.assertNotContains(respuesta, 'html2canvas')
        self.assertNotContains(respuesta, 'descargarPantallaPDF')
        self.assertNotContains(respuesta, 'captura de pantalla')
