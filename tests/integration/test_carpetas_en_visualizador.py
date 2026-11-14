"""Las carpetas y archivos propios del menú se renombran, cambian de visibilidad y suman subcarpetas desde el mismo
visualizador; ocultar, mover y eliminar siguen en el organizador, donde lo oculto queda a la vista."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.directorio_unidades.models.core import Unidad


class CarpetasEnElVisualizadorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-carpetas-visor', 'c@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con carpetas', slug='lab-carpetas-visor',
                                        dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        modulo = ModuloUnidad.objects.get(unidad=cls.lab, clave='areas-equipos')
        cls.carpeta = CarpetaRecurso.objects.create(unidad=cls.lab, nombre='Inventario', modulo_config=modulo,
                                                    seccion_planta='2.4', visibilidad='publica')
        cls.archivo = Recurso.objects.create(unidad=cls.lab, carpeta=cls.carpeta, nombre='Inventario Laboratorio',
                                             url='https://www.upec.edu.ec/', seguridad_verificada=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def url(self, clave, pk):
        return reverse('editar_registro', args=[self.lab.slug, clave, pk])

    def test_el_menu_ofrece_editar_carpetas_y_archivos(self):
        ficha = self.client.get(self.lab.get_absolute_url()).content.decode()
        self.assertIn(self.url('carpeta', self.carpeta.pk), ficha)
        self.assertIn(self.url('archivo', self.archivo.pk), ficha)
        self.assertIn(f"{self.url('carpeta', 'nuevo')}?padre={self.carpeta.pk}", ficha)
        self.assertIn(f'{reverse("admin:recursos_recurso_add")}?unidad={self.lab.pk}&amp;carpeta={self.carpeta.pk}', ficha)
        self.assertIn('edicion_en_ficha.js', ficha)

    def test_renombrar_cambiar_visibilidad_y_crear_subcarpeta(self):
        self.client.post(self.url('carpeta', self.carpeta.pk), {'registro-nombre': 'Inventario 2026',
                                                               'registro-visibilidad': 'restringida'})
        self.carpeta.refresh_from_db()
        self.assertEqual((self.carpeta.nombre, self.carpeta.visibilidad), ('Inventario 2026', 'restringida'))
        formulario = self.client.get(self.url('archivo', self.archivo.pk), {'fragmento': '1'})
        self.assertNotContains(formulario, 'name="registro-archivo"')
        self.client.post(self.url('archivo', self.archivo.pk), {'registro-nombre': 'Inventario general',
                                                               'registro-descripcion': 'Equipos del laboratorio.',
                                                               'registro-visibilidad': 'publica'})
        self.archivo.refresh_from_db()
        self.assertEqual(self.archivo.nombre, 'Inventario general')
        self.client.post(f"{self.url('carpeta', 'nuevo')}?padre={self.carpeta.pk}", {
            'registro-nombre': 'Equipos de captura', 'registro-visibilidad': 'publica'})
        hija = CarpetaRecurso.objects.get(nombre='Equipos de captura')
        self.assertEqual((hija.carpeta_padre, hija.seccion_planta, hija.modulo_config_id),
                         (self.carpeta, '2.4', self.carpeta.modulo_config_id))
        # No hay tercer nivel: una subcarpeta no recibe otra.
        self.assertEqual(self.client.get(f"{self.url('carpeta', 'nuevo')}?padre={hija.pk}").status_code, 404)
