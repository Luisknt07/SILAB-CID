"""Tipologias administrables: catalogo, desactivacion en servidor y ruta generica."""
from datetime import date
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import translation

from apps.configuracion_institucional.tipologias.models import TipologiaUnidad, sembrar_bases
from apps.core.presentation.tipologias import (
    nombre_tipologia,
    opciones_tipologias,
    tipologia_activa,
    tipologias_actuales,
    tipologias_de_despliegue,
    tipologias_publicas,
)
from apps.core.tipologias import CODIGOS_BASE, Tipologia, catalogo_tipologias
from apps.directorio_unidades.models.core import Unidad


class ContratoTipologiasTests(SimpleTestCase):
    def test_catalogo_base_valido_ordenado_y_bilingue(self):
        catalogo = catalogo_tipologias(tipologias_de_despliegue())
        self.assertEqual(tuple(t.codigo for t in catalogo), CODIGOS_BASE)
        laboratorio = catalogo[0]
        self.assertEqual(laboratorio.etiqueta('en', plural=True), 'Laboratories')
        self.assertEqual(laboratorio.etiqueta('es'), 'Laboratorio')
        self.assertEqual(Tipologia('x', 'X', 'Xs', 'laboratorios').etiqueta('en'), 'X')

    def test_rechaza_codigos_iconos_bases_y_duplicados_invalidos(self):
        valida = Tipologia('invernaderos', 'Invernadero', 'Invernaderos', 'laboratorios')
        for invalida in (
            Tipologia('Invernaderos', 'Invernadero', 'Invernaderos', 'laboratorios'),
            Tipologia('invernaderos', 'Invernadero', 'Invernaderos', 'laboratorios', icono='<script>'),
            Tipologia('invernaderos', '', 'Invernaderos', 'laboratorios'),
            Tipologia('invernaderos', 'Inver<nadero>', 'Invernaderos', 'laboratorios'),
            Tipologia('invernaderos', 'Invernadero', 'Invernaderos', 'invernaderos'),
            Tipologia('laboratorios', 'Laboratorio', 'Laboratorios', 'plantas_piloto'),
            Tipologia('invernaderos', 'Invernadero', 'Invernaderos', 'laboratorios', orden=-1),
        ):
            with self.subTest(invalida=invalida), self.assertRaises(ValueError):
                catalogo_tipologias((*tipologias_de_despliegue(), invalida))
        with self.assertRaises(ValueError):
            catalogo_tipologias((*tipologias_de_despliegue(), valida, valida))
        with self.assertRaises(ValueError):
            catalogo_tipologias((valida,))


class CatalogoInstitucionalTests(TestCase):
    def setUp(self):
        # Un TransactionTestCase previo vacia la semilla de la migracion; la
        # misma funcion la restaura de forma idempotente.
        sembrar_bases(TipologiaUnidad)
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-tipologias', email='tipologias@upec.edu.ec', password='clave-segura-pruebas',
        )
        self.client.force_login(self.usuario)

    def crear_unidad(self, dependencia, slug):
        return Unidad.objects.create(
            nombre=f'Unidad {slug}', slug=slug, dependencia=dependencia,
            descripcion='Unidad de prueba', fecha_inicio=date(2026, 1, 1),
            modo_operacion='lotes' if dependencia == 'plantas_piloto' else '',
        )

    def test_la_semilla_conserva_las_cuatro_implementadas_y_no_se_eliminan(self):
        sembrar_bases(TipologiaUnidad)  # repetir no duplica ni altera filas
        self.assertEqual(
            list(TipologiaUnidad.objects.values_list('codigo', flat=True)), list(CODIGOS_BASE),
        )
        TipologiaUnidad.objects.filter(codigo='laboratorios').delete()
        self.assertEqual(tuple(t.codigo for t in tipologias_actuales()), CODIGOS_BASE)
        sembrar_bases(TipologiaUnidad)
        with self.assertRaises(ValidationError):
            TipologiaUnidad.objects.get(codigo='laboratorios').delete()
        implementada = TipologiaUnidad.objects.get(codigo='observatorios')
        implementada.base = 'laboratorios'
        with self.assertRaises(ValidationError):
            implementada.full_clean()

    def test_una_tipologia_nueva_aparece_en_pestanas_ruta_generica_y_admin(self):
        TipologiaUnidad.objects.create(
            codigo='invernaderos', nombre='Invernadero', nombre_plural='Invernaderos',
            nombre_en='Greenhouse', nombre_plural_en='Greenhouses', icono='iconsminds-plant', orden=5,
        )
        propia = self.crear_unidad('invernaderos', 'invernadero-norte')
        ajena = self.crear_unidad('laboratorios', 'laboratorio-quimica')
        self.assertEqual(propia.modulos_contenido.count(), ajena.modulos_contenido.count())
        self.assertEqual(propia.clasificacion_funcional, 'laboratorio_academico')

        catalogo = self.client.get(reverse('hublab'))
        url_generica = reverse('catalogo_tipologia', kwargs={'tipologia': 'invernaderos'})
        self.assertContains(catalogo, f'href="{url_generica}"')
        self.assertContains(catalogo, 'data-tipologia="invernaderos"')
        self.assertNotContains(catalogo, propia.nombre)

        respuesta = self.client.get(url_generica)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['catalogo_titulo'], 'Invernaderos')
        self.assertContains(respuesta, propia.nombre)
        self.assertContains(respuesta, '<i class="iconsminds-plant"></i>')
        self.assertContains(respuesta, 'lab-unit-card--laboratorios')
        self.assertNotContains(respuesta, ajena.nombre)

        with translation.override('en'):
            self.assertEqual(nombre_tipologia('invernaderos', plural=True), 'Greenhouses')
        detalle = self.client.get(propia.get_absolute_url())
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, 'Invernadero')

        formulario = self.client.get(reverse('admin:directorio_unidades_unidad_add'))
        self.assertContains(formulario, '<option value="invernaderos">Invernadero</option>', html=True)

    def test_la_ruta_generica_redirige_las_implementadas_y_rechaza_desconocidas(self):
        for codigo in CODIGOS_BASE:
            with self.subTest(codigo=codigo):
                respuesta = self.client.get(reverse('catalogo_tipologia', kwargs={'tipologia': codigo}))
                self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            self.client.get(reverse('catalogo_tipologia', kwargs={'tipologia': 'no-existe'})).status_code, 404,
        )

    def test_desactivar_una_tipologia_retira_su_superficie_publica_y_conserva_datos(self):
        unidad = self.crear_unidad('observatorios', 'observatorio-clima')
        TipologiaUnidad.objects.filter(codigo='observatorios').update(activa=False)

        self.assertFalse(tipologia_activa('observatorios'))
        self.assertNotIn('observatorios', [t.codigo for t in tipologias_publicas()])
        self.assertEqual(self.client.get(reverse('observatorios')).status_code, 404)
        self.assertEqual(self.client.get(unidad.get_absolute_url()).status_code, 404)
        self.assertEqual(
            self.client.get(reverse('catalogo_tipologia', kwargs={'tipologia': 'observatorios'})).status_code, 404,
        )
        catalogo = self.client.get(reverse('hublab'))
        self.assertEqual(catalogo.status_code, 200)
        self.assertNotContains(catalogo, 'data-tipologia="observatorios"')
        self.assertContains(catalogo, 'data-tipologia="plantas_piloto"')
        unidad.refresh_from_db()
        self.assertEqual(unidad.dependencia, 'observatorios')
        self.assertTrue(unidad.modulos_contenido.exists())

        # La unidad existente conserva su tipologia en el formulario, pero una
        # unidad nueva ya no puede elegirla.
        self.assertEqual([c for c, _ in opciones_tipologias()], [c for c in CODIGOS_BASE if c != 'observatorios'])
        self.assertIn('observatorios', [c for c, _ in opciones_tipologias(incluir='observatorios')])
        edicion = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk]))
        self.assertContains(edicion, '<option value="observatorios" selected>Observatorio</option>', html=True)
        alta = self.client.get(reverse('admin:directorio_unidades_unidad_add'))
        self.assertNotContains(alta, 'value="observatorios"')

        TipologiaUnidad.objects.filter(codigo='observatorios').update(activa=True)
        self.assertEqual(self.client.get(unidad.get_absolute_url()).status_code, 200)

    def test_una_unidad_rechaza_una_tipologia_fuera_del_catalogo(self):
        unidad = Unidad(nombre='Sin catálogo', slug='sin-catalogo', dependencia='inexistente',
                        descripcion='x', fecha_inicio=date(2026, 1, 1))
        with self.assertRaises(ValidationError) as contexto:
            unidad.full_clean()
        self.assertIn('dependencia', contexto.exception.message_dict)
        registro = admin.site._registry[Unidad]
        peticion = RequestFactory().get('/')
        peticion.user = self.usuario
        formulario = registro.get_form(peticion)(data={'dependencia': 'inexistente'})
        self.assertIn('dependencia', formulario.errors)

    def test_el_proveedor_falla_cerrado_a_las_implementadas(self):
        TipologiaUnidad.objects.create(codigo='invernaderos', nombre='Invernadero', nombre_plural='Invernaderos')
        with patch('apps.configuracion_institucional.tipologias.selectors.TipologiaUnidad.objects') as objetos, \
                self.assertLogs('apps.configuracion_institucional.tipologias.selectors', level='WARNING'):
            objetos.using.return_value.all.side_effect = DatabaseError('sin base')
            self.assertEqual(tuple(t.codigo for t in tipologias_actuales()), CODIGOS_BASE)
        self.assertIn('invernaderos', [t.codigo for t in tipologias_actuales()])


class PuertaDelDirectorioTests(TestCase):
    """La ruta historica de Laboratorios es tambien la puerta del directorio."""

    def setUp(self):
        sembrar_bases(TipologiaUnidad)
        self.planta = Unidad.objects.create(
            nombre='Planta de lácteos', slug='planta-lacteos', dependencia='plantas_piloto',
            descripcion='x', fecha_inicio=date(2026, 1, 1))

    def test_desactivar_laboratorios_no_cierra_la_puerta_a_los_demas_tipos(self):
        """El menu, la portada y el perfil enlazan la puerta; tiene que seguir abriendo."""
        TipologiaUnidad.objects.filter(codigo='laboratorios').update(activa=False)

        for ruta in ('laboratorios_unidades', 'hublab'):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(reverse(ruta))
                # El orden institucional: laboratorios, observatorios, centros, plantas.
                self.assertRedirects(respuesta, reverse('observatorios'), fetch_redirect_response=False)
        catalogo = self.client.get(reverse('plantas-piloto'))
        self.assertEqual(catalogo.status_code, 200)
        self.assertNotContains(catalogo, 'data-tipologia="laboratorios"')
        self.assertContains(catalogo, 'data-tipologia="plantas_piloto"')
        self.assertEqual(self.client.get(self.planta.get_absolute_url()).status_code, 200)

    def test_sin_ningun_tipo_activo_la_puerta_si_se_cierra(self):
        TipologiaUnidad.objects.update(activa=False)

        self.assertEqual(self.client.get(reverse('laboratorios_unidades')).status_code, 404)
        self.assertEqual(self.client.get(self.planta.get_absolute_url()).status_code, 404)

    def test_con_laboratorios_activo_la_puerta_es_su_catalogo(self):
        respuesta = self.client.get(reverse('laboratorios_unidades'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-tipologia="laboratorios"')


class InterruptorDePublicacionTests(TestCase):
    """Cada area de tipo trae la casilla que publica o retira el tipo entero."""

    def setUp(self):
        sembrar_bases(TipologiaUnidad)
        self.superusuario = get_user_model().objects.create_superuser('interruptor.qa')
        self.laboratorio = Unidad.objects.create(
            nombre='Lab de suelos', slug='lab-suelos', dependencia='laboratorios',
            descripcion='x', fecha_inicio=date(2026, 1, 1))
        self.url = reverse('admin:configuracion_institucional_tipologiaunidad_publicacion',
                           args=['laboratorios'])

    def area(self, respuesta, slug):
        return next(a for a in respuesta.context['app_list'] if a['slug'] == slug)

    def test_el_area_del_tipo_muestra_su_casilla_con_el_estado_actual(self):
        self.client.force_login(self.superusuario)
        indice = self.client.get(reverse('admin:index'))

        publicacion = self.area(indice, 'laboratorios')['publicacion']
        self.assertEqual([(p['codigo'], p['activa']) for p in publicacion], [('laboratorios', True)])
        self.assertEqual(publicacion[0]['url'], self.url)
        self.assertContains(indice, 'data-publicacion-tipo checked')
        # Las areas transversales no tienen tipo que publicar.
        self.assertEqual(self.area(indice, 'usuarios').get('publicacion'), [])

    def test_la_casilla_retira_y_vuelve_a_publicar_el_tipo_entero(self):
        self.client.force_login(self.superusuario)

        respuesta = self.client.post(self.url, {'volver': 'laboratorios'})

        self.assertRedirects(respuesta, reverse('admin:index') + '#laboratorios',
                             fetch_redirect_response=False)
        self.assertFalse(TipologiaUnidad.objects.get(codigo='laboratorios').activa)
        self.assertEqual(self.client.get(self.laboratorio.get_absolute_url()).status_code, 404)
        self.assertContains(self.client.get(reverse('admin:index')), 'retirado del público')

        self.client.post(self.url, {'volver': 'laboratorios', 'activa': '1'})

        self.assertTrue(TipologiaUnidad.objects.get(codigo='laboratorios').activa)
        self.assertEqual(self.client.get(self.laboratorio.get_absolute_url()).status_code, 200)

    def test_sin_permiso_de_edicion_no_hay_casilla_ni_cambio(self):
        personal = get_user_model().objects.create_user('personal.qa', is_staff=True)
        self.client.force_login(personal)

        self.assertEqual(self.client.post(self.url, {'volver': 'laboratorios'}).status_code, 403)
        self.assertTrue(TipologiaUnidad.objects.get(codigo='laboratorios').activa)

    def test_solo_se_cambia_enviando_el_formulario(self):
        self.client.force_login(self.superusuario)

        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(TipologiaUnidad.objects.get(codigo='laboratorios').activa)
