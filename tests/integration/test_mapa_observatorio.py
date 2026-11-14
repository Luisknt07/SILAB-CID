"""El mapa de un observatorio: seis pestañas propias de quien produce información para decidir.

Un observatorio produce datos, pero tiene su sala, sus equipos y su software: su última pestaña no es la agenda de
reservas de un laboratorio, sino las solicitudes de datos (también para usar la sala), los cursos, las visitas y el
acceso a los datos. La ficha pública numera sus secciones, enlaza «Conoce la unidad» y no ofrece al público pestañas sin
nada publicado; quien gestiona las ve marcadas. La reorganización le apaga las reservas, el contenido de prueba se
retira sin borrarse y un archivo sin revisión de seguridad nunca se publica.
"""
from datetime import date
from io import StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.gestion_unidades.presentation.portadas import portadas_de
from apps.formacion.presentation.recursos_publicos import _acceso_recurso
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_OBSERVATORIO, mapa_de
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.presentacion import HitoUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.recursos import DEFAULT_MODULES_BY_DEPENDENCIA


class MapaDeObservatorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.observatorio = Unidad.objects.create(
            nombre='Observatorio de prueba', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='observatorio-de-prueba', dependencia='observatorios', clasificacion_funcional='observatorio')
        cls.centro = Unidad.objects.create(
            nombre='Centro de prueba', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='centro-de-prueba', dependencia='centro_experimental')
        cls.admin = get_user_model().objects.create_superuser('obs.admin', 'o@example.org', 'clave')

    def test_el_mapa_sigue_las_pestanas_del_observatorio_sin_agenda_de_reservas(self):
        self.assertIs(mapa_de(self.observatorio), MAPA_OBSERVATORIO)
        self.assertEqual(list(MAPA_OBSERVATORIO.pestanas),
                         [clave for clave, *_ in DEFAULT_MODULES_BY_DEPENDENCIA['observatorios']])
        self.assertEqual(len(MAPA_OBSERVATORIO.secciones), 25)
        self.assertEqual(MAPA_OBSERVATORIO.modulo_reservas, '')
        self.assertEqual((MAPA_OBSERVATORIO.numero('indicadores'), MAPA_OBSERVATORIO.numero('alertas'),
                          MAPA_OBSERVATORIO.numero('boletines'), MAPA_OBSERVATORIO.numero('solicitudes')),
                         ('2.1', '2.2', '3.1', '5.1'))
        self.assertEqual((MAPA_OBSERVATORIO.numero('guias'), MAPA_OBSERVATORIO.numero('cursos'),
                          MAPA_OBSERVATORIO.numero('visitas'), MAPA_OBSERVATORIO.numero('visitas_observatorio'),
                          MAPA_OBSERVATORIO.numero('sala'), MAPA_OBSERVATORIO.numero('tableros'),
                          MAPA_OBSERVATORIO.numero('politica_datos'), MAPA_OBSERVATORIO.numero('impacto')),
                         ('', '5.4', '', '', '5.5', '2.3', '1.5', '4.5'))
        self.assertEqual((MAPA_OBSERVATORIO.numero('lineas'), MAPA_OBSERVATORIO.numero('visores'),
                          MAPA_OBSERVATORIO.numero('actualizaciones'), MAPA_OBSERVATORIO.numero('fuentes')),
                         ('1.3', '2.4', '', '2.7'))
        self.assertIsNot(mapa_de(self.centro), MAPA_OBSERVATORIO)

    def test_el_publico_solo_ve_lo_publicado_y_quien_gestiona_ve_las_secciones_pendientes(self):
        url = self.observatorio.get_absolute_url()
        publico = self.client.get(url)
        self.assertEqual(publico.status_code, 200)
        self.assertContains(publico, 'Información general')
        self.assertNotContains(publico, 'Datos y monitoreo')
        self.client.force_login(self.admin)
        gestion = self.client.get(url)
        self.assertContains(gestion, 'Datos y monitoreo')
        self.assertContains(gestion, 'Fuentes y actualización')
        self.assertNotContains(gestion, 'Monitoreo y alertas')
        self.assertContains(gestion, 'Qué ofrece y qué no')
        self.assertContains(gestion, 'Política de datos')

    def test_la_foto_de_portada_con_licencia_abierta_muestra_su_credito(self):
        media = TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(media.cleanup)
        with override_settings(MEDIA_ROOT=media.name):
            self.observatorio.imagen = SimpleUploadedFile('portada.jpg', b'jpg', content_type='image/jpeg')
            self.observatorio.credito_imagen = 'Laguna del Voladero · Autor · CC BY-SA 4.0'
            self.observatorio.credito_imagen_url = 'https://commons.wikimedia.org/wiki/File:Voladero.jpg'
            self.observatorio.save()
            ficha = self.client.get(self.observatorio.get_absolute_url())
        self.assertContains(ficha, 'Laguna del Voladero · Autor · CC BY-SA 4.0')
        self.assertContains(ficha, 'https://commons.wikimedia.org/wiki/File:Voladero.jpg')

    def test_las_portadas_del_observatorio_no_se_prestan_al_centro_experimental(self):
        obs = {p['clave']: p for p in portadas_de(self.observatorio, self.observatorio.modulos_contenido.all())}
        centro = {p['clave']: p for p in portadas_de(self.centro, self.centro.modulos_contenido.all())}
        self.assertIn('Las encuestas propias', obs['investigacion-vinculacion']['como_leerlo'][0])
        self.assertNotIn('Las encuestas propias', centro['investigacion-vinculacion']['como_leerlo'][0])

    def test_la_reorganizacion_apaga_las_reservas_de_los_observatorios(self):
        call_command('reorganizar_unidades', stdout=StringIO())
        turismo = Unidad.objects.get(slug='observatorio-turismo')
        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=turismo)
        self.assertFalse(configuracion.reservas_espacios or configuracion.reservas_equipos
                         or configuracion.solicitudes_servicio or configuracion.consumibles)
        self.assertEqual(list(turismo.modulos_contenido.filter(activo=True).values_list('clave', flat=True)),
                         list(MAPA_OBSERVATORIO.pestanas))


class ContenidoDePruebaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.turismo = Unidad.objects.create(
            nombre='Observatorio de Turismo', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='observatorio-turismo', dependencia='observatorios')
        cls.logistica = Unidad.objects.create(
            nombre='Laboratorio de Logística', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-logistica-prueba', dependencia='laboratorios')
        cls.xr = Unidad.objects.create(
            nombre='Laboratorio XR', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-realidad-extendida', dependencia='laboratorios')

    def setUp(self):
        media = TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))

    def carpeta(self, unidad, **recurso):
        carpeta = CarpetaRecurso.objects.create(nombre='📂 Presentación del Laboratorio XR', unidad=unidad,
                                                modulo_config=unidad.modulos_contenido.first(), visibilidad='publica')
        if recurso:
            Recurso.objects.create(unidad=unidad, carpeta=carpeta, archivo=SimpleUploadedFile('a.html', b'<p>x</p>'),
                                   **recurso)
        return carpeta

    def test_un_archivo_sin_revision_no_se_publica_aunque_no_tenga_descripcion(self):
        carpeta = self.carpeta(self.turismo, nombre='Simulador y recorrido 360', descripcion='')
        recurso = carpeta.recursos.get()
        self.assertEqual(_acceso_recurso(recurso, get_user_model()()), 'denegado')
        recurso.seguridad_verificada = True
        self.assertEqual(_acceso_recurso(recurso, get_user_model()()), 'permitido')

    def test_la_limpieza_desactiva_las_pruebas_renombra_lo_real_y_respeta_al_dueno(self):
        prueba = self.carpeta(self.turismo, nombre='Simulador y recorrido 360', descripcion='')
        real = self.carpeta(self.logistica, nombre='WMS', descripcion='Simulador del almacén.', seguridad_verificada=True)
        propia = self.carpeta(self.xr, nombre='Recorrido', descripcion='Recorrido XR.', seguridad_verificada=True)
        HitoUnidad.objects.create(unidad=self.turismo, anio=2026,
                                  titulo='Áreas, equipos e inventario documentados en la plataforma')
        call_command('limpiar_contenido_de_prueba', '--simular', stdout=StringIO())
        prueba.refresh_from_db()
        self.assertTrue(prueba.activa)
        call_command('limpiar_contenido_de_prueba', stdout=StringIO())
        for carpeta in (prueba, real, propia):
            carpeta.refresh_from_db()
        self.assertFalse(prueba.activa)
        self.assertFalse(prueba.recursos.get().activo)
        self.assertEqual((real.activa, real.nombre), (True, '📂 Recursos del laboratorio'))
        self.assertEqual(propia.nombre, '📂 Presentación del Laboratorio XR')
        self.assertTrue(HitoUnidad.objects.filter(unidad=self.turismo,
                                                  titulo='Registro en la plataforma institucional').exists())
        self.assertIn('Nada que limpiar', self._repetir())

    def _repetir(self):
        salida = StringIO()
        call_command('limpiar_contenido_de_prueba', stdout=salida)
        return salida.getvalue()
