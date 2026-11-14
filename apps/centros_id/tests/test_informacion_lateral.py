"""Áreas completas y ficha lateral con datos públicos del centro seleccionado."""
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import router
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.contenidos import Contenidos
from apps.centros_id.models import Articulacion, CentroID, Componente, Integrante


@override_settings(CENTROS_ID_ESCENARIOS_OPERATIVOS=())
class InformacionLateralTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}

    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroID.objects.create(
            nombre='Centro de capacidades', sigla='CIC', slug='centro-capacidades',
            proposito='Investigación aplicada', area='digitales',
            adscripcion='Vicerrectorado de Investigación', mision='Misión registrada',
            vision='Visión registrada', fuente_identidad='Resolución institucional',
            identidad_validada_en=timezone.now(),
            contacto_email='centro@example.org', ubicacion='Edificio de investigación',
            direccion='Tulcán, Ecuador', horario_atencion='Lunes a viernes, 08:00–17:00',
        )
        for numero in range(7):
            Componente.objects.create(
                centro=cls.centro, codigo=f'area-{numero}', nombre=f'Área publicada {numero}',
                tipo='division', resumen='Capacidad del centro', descripcion='Descripción', publicado=True,
            )
        Componente.objects.create(
            centro=cls.centro, codigo='no-publicada', nombre='Área oculta para revisión',
            tipo='division', resumen='Pendiente', descripcion='Pendiente', publicado=False,
        )
        Integrante.objects.create(centro=cls.centro, nombre='Dirección pública',
                                  rol='director', cargo='Directora del centro')
        Integrante.objects.create(centro=cls.centro, nombre='Dirección de muestra reservada',
                                  rol='director', es_muestra=True, orden=0)
        Integrante.objects.create(centro=cls.centro, nombre='Dirección anterior reservada',
                                  rol='director', vigente=False)
        for nombre in ('Computación', 'Logística y Transporte', 'Computación'):
            Articulacion.objects.create(centro=cls.centro, tipo='carrera', actor=nombre)
        cls.otro = CentroID.objects.create(
            nombre='Otro centro independiente', slug='otro-centro', area='digitales', proposito='Otro ámbito',
        )

    def ficha(self, centro=None):
        return self.client.get(reverse('centro_id', args=[(centro or self.centro).slug]))

    def test_el_catalogo_muestra_todas_las_areas_publicadas_y_las_enlaza(self):
        pagina = self.client.get(reverse('centros_id'))
        tarjeta = next(c for c in pagina.context['centros'] if c.pk == self.centro.pk)
        self.assertEqual(len(tarjeta.areas_tarjeta), 7)
        for numero in range(7):
            self.assertContains(pagina, f'Área publicada {numero}')
            self.assertContains(pagina, f'{reverse("centro_id", args=[self.centro.slug])}?area=area-{numero}')
        self.assertNotContains(pagina, 'Área oculta para revisión')
        self.assertNotContains(pagina, 'Áreas destacadas')

    def test_la_informacion_aparece_debajo_de_contenidos_con_cifras_del_centro(self):
        pagina = self.ficha()
        texto = pagina.content.decode()
        self.assertGreater(texto.index('id="cidInformacion"'), texto.index('cid-panel--contenidos'))
        for dato in ('Información del centro', 'Vicerrectorado de Investigación',
                     'Dirección pública', 'centro@example.org',
                     'Edificio de investigación', 'Lunes a viernes, 08:00–17:00',
                     'Capacidades del centro', 'Computación', 'Logística y Transporte'):
            self.assertContains(pagina, dato)
        self.assertContains(pagina, 'mailto:centro@example.org')
        self.assertContains(pagina, '?seccion=ubicacion')
        self.assertContains(pagina, '?seccion=identidad')
        self.assertContains(pagina, 'Ver ficha completa')
        self.assertEqual(pagina.context['institutional_active_page'], 'centros')
        self.assertContains(pagina, '<a class="active" href="/centros-id/">')
        ficha_completa = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'identidad']))
        self.assertContains(ficha_completa, 'Directora del centro')
        informacion = pagina.context['c'].informacion_general
        self.assertEqual(informacion['carreras'], ['Computación', 'Logística y Transporte'])
        self.assertEqual({c['clave']: c['valor'] for c in informacion['cifras']},
                         {'areas': 7, 'servicios': 0, 'vinculadas': 0, 'lineas': 0})
        self.assertEqual(informacion['editar_url'], '')

    def test_no_publica_adscripcion_sin_validacion_ni_direcciones_ocultas(self):
        CentroID.objects.filter(pk=self.centro.pk).update(identidad_validada_en=None)
        pagina = self.ficha()
        for dato in ('Vicerrectorado de Investigación', 'Dirección de muestra reservada',
                     'Dirección anterior reservada'):
            self.assertNotContains(pagina, dato)
        self.assertContains(pagina, 'Estado pendiente de validación')

    def test_no_mezcla_informacion_de_otro_centro_ni_inventa_datos(self):
        pagina = self.ficha(self.otro)
        self.assertContains(pagina, 'Información del centro')
        self.assertContains(pagina, 'Capacidades del centro')
        for dato in ('centro@example.org', 'Dirección pública', 'Vicerrectorado de Investigación',
                     'Logística y Transporte', 'Facultad por registrar', 'Por asignar'):
            self.assertNotContains(pagina, dato)
        self.assertTrue(all(c['valor'] == 0 for c in pagina.context['c'].informacion_general['cifras']))

    def test_el_panel_reutiliza_las_colecciones_sin_consultas_adicionales(self):
        contenido = Contenidos(self.centro, AnonymousUser())
        for nombre in ('areas', 'servicios', 'lineas', 'articulaciones', 'integrantes'):
            getattr(contenido, nombre)
        with self.assertNumQueries(0, using=router.db_for_read(CentroID)):
            informacion = contenido.informacion_general
            self.assertIs(informacion, contenido.informacion_general)
            self.assertEqual(informacion['cifras'][0]['valor'], 7)
