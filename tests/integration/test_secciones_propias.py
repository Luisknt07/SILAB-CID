"""Secciones nuevas de la ficha creadas desde una plantilla: nacen con muestras que solo ve quien gestiona, se editan
en su propia página con el estilo de las comunes y aparecen en el menú de su pestaña, numeradas tras las comunes."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.formacion.presentation.aula import contexto_aula
from apps.gestion_unidades.models.secciones_propias import ElementoSeccionPropia, SeccionPropia
from apps.recursos.models.recursos import ModuloUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class SeccionesPropiasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.coordinador = User.objects.create_user('coordina-secciones', password='clave')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.visitante = User.objects.create_user('visita-secciones', password='clave')
        identificar(cls.visitante, tipo_usuario='estudiante')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con secciones', slug='lab-secciones-propias',
                                        dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                        administrador=cls.coordinador)
        cls.areas = ModuloUnidad.objects.get(unidad=cls.lab, clave='areas-equipos')
        cls.nueva = reverse('nueva_seccion_propia', args=[cls.lab.slug])

    def setUp(self):
        self.client.force_login(self.coordinador)

    def crear(self, titulo='Convenios y alianzas', plantilla='tarjetas'):
        respuesta = self.client.post(self.nueva, {'titulo': titulo, 'plantilla': plantilla, 'modulo': self.areas.pk},
                                     HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        return SeccionPropia.objects.get(unidad=self.lab, titulo=titulo)

    def menu(self, usuario=None):
        modulos = ModuloUnidad.objects.filter(unidad=self.lab, activo=True)
        return [c for c in contexto_aula(self.lab, modulos, usuario)['aula']['carpetas'] if c.get('propia')]

    def test_nace_con_muestras_que_solo_ve_quien_gestiona(self):
        self.assertContains(self.client.get(self.nueva, {'fragmento': '1', 'modulo': self.areas.pk}), 'Nueva sección con plantilla')
        seccion = self.crear()
        self.assertEqual(seccion.elementos.filter(es_ejemplo=True).count(), 3)
        url = reverse('seccion_propia', args=[self.lab.slug, seccion.pk])
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Sección 2.5 · Laboratorio con secciones')
        self.assertContains(pagina, 'Plantilla lista para completar.')
        self.assertContains(pagina, 'area__actividad')
        self.assertContains(pagina, 'data-editar-ficha')
        # Para el público, una sección solo con muestras no existe ni aparece en el menú.
        self.client.force_login(self.visitante)
        self.assertEqual(self.menu(self.visitante), [])
        self.assertNotContains(self.client.get(url), 'Primer elemento')
        self.assertEqual(len(self.menu(self.coordinador)), 1)

    def test_editar_una_muestra_la_publica_y_la_seccion_aparece_en_el_menu(self):
        seccion = self.crear(plantilla='pasos')
        muestra = seccion.elementos.first()
        editar = reverse('editar_seccion_propia', args=[self.lab.slug, seccion.pk])
        formulario = self.client.get(editar, {'elemento': muestra.pk, 'fragmento': '1'})
        self.assertContains(formulario, 'Es un elemento de muestra')
        self.client.post(editar, {'elemento': muestra.pk, 'elemento-titulo': 'Firma del convenio',
                                  'elemento-descripcion': 'Se firma con la otra institución.', 'elemento-orden': '1',
                                  'elemento-activo': 'on'}, HTTP_X_REQUESTED_WITH='fetch')
        muestra.refresh_from_db()
        self.assertEqual((muestra.titulo, muestra.es_ejemplo), ('Firma del convenio', False))
        self.client.post(editar, {'elemento': 'nuevo', 'elemento-titulo': 'Seguimiento', 'elemento-orden': '9',
                                  'elemento-activo': 'on'})
        self.client.post(editar, {'elemento': seccion.elementos.filter(es_ejemplo=True).first().pk,
                                  'elemento-titulo': 'x', 'elemento-orden': '1', 'elemento-eliminar': 'on'})
        self.assertEqual(seccion.elementos.count(), 3)
        carpetas = self.menu(self.visitante)
        self.assertEqual([c['titulo'] for c in carpetas], ['Convenios y alianzas'])
        self.assertEqual(carpetas[0]['total'], 2)
        self.client.force_login(self.visitante)
        pagina = self.client.get(reverse('seccion_propia', args=[self.lab.slug, seccion.pk]))
        self.assertContains(pagina, 'Firma del convenio')
        self.assertContains(pagina, 'area__pasos')
        self.assertNotContains(pagina, 'data-editar-ficha')
        self.assertEqual(self.client.get(editar).status_code, 403)

    def test_los_datos_de_la_seccion_y_su_plantilla_se_editan(self):
        seccion = self.crear()
        editar = reverse('editar_seccion_propia', args=[self.lab.slug, seccion.pk])
        self.client.post(editar, {'seccion-titulo': 'Alianzas', 'seccion-resumen': 'Con quién trabajamos',
                                  'seccion-plantilla': 'tabla', 'seccion-icono': 'fas fa-handshake'})
        seccion.refresh_from_db()
        self.assertEqual((seccion.titulo, seccion.plantilla, seccion.activa), ('Alianzas', 'tabla', False))
        self.assertContains(self.client.get(reverse('seccion_propia', args=[self.lab.slug, seccion.pk])), 'area__tabla')
        # El menú de la unidad ofrece crearla a quien coordina, al final de cada pestaña.
        self.assertContains(self.client.get(self.lab.get_absolute_url()), f'{self.nueva}?modulo={self.areas.pk}')

    def test_el_organizador_crea_ordena_oculta_y_elimina(self):
        admin = get_user_model().objects.create_superuser('admin-secciones', 'a@example.org', 'clave')
        self.client.force_login(admin)
        url = reverse('admin:directorio_unidades_unidad_contenidos', args=[self.lab.pk])
        self.client.post(url, {'accion': 'crear_seccion_propia', 'modulo': self.areas.pk, 'nombre': 'Galería 360',
                               'plantilla': 'texto'})
        self.client.post(url, {'accion': 'crear_seccion_propia', 'modulo': self.areas.pk, 'nombre': 'Convenios',
                               'plantilla': 'tarjetas'})
        galeria, convenios = SeccionPropia.objects.filter(unidad=self.lab).order_by('orden')
        self.assertContains(self.client.get(url), 'Secciones con plantilla')
        self.client.post(url, {'accion': 'ordenar_seccion_propia', 'seccion_propia': convenios.pk, 'direccion': 'subir'})
        self.assertEqual(list(SeccionPropia.objects.filter(unidad=self.lab).order_by('orden').values_list('titulo', flat=True)),
                         ['Convenios', 'Galería 360'])
        self.client.post(url, {'accion': 'alternar_seccion_propia', 'seccion_propia': galeria.pk})
        galeria.refresh_from_db()
        self.assertFalse(galeria.activa)
        ElementoSeccionPropia.objects.filter(seccion=convenios).update(es_ejemplo=False)
        respuesta = self.client.post(url, {'accion': 'eliminar_seccion_propia', 'seccion_propia': convenios.pk}, follow=True)
        self.assertContains(respuesta, 'Solo se elimina una sección sin contenido propio')
        self.client.post(url, {'accion': 'eliminar_seccion_propia', 'seccion_propia': galeria.pk})
        self.assertFalse(SeccionPropia.objects.filter(pk=galeria.pk).exists())
