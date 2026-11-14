"""Cada sección del menú agrega su propio elemento con la plantilla que ya usa (una nueva área con la página de las
áreas, un equipo con su ficha técnica, un programa, un proceso…), con texto guía y sin publicarse hasta completarlo,
y cualquier sección suma carpetas propias desde el mismo visualizador."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class AltasDesdeElMenuTests(TestCase):
    databases = {'default', 'centros'}
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser('admin-altas', 'a@example.org', 'clave')
        cls.visitante = User.objects.create_user('visita-altas', password='clave')
        identificar(cls.visitante, tipo_usuario='estudiante')
        cls.lab = Unidad.objects.create(nombre='Laboratorio de altas', slug='lab-altas', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.area = EspacioReservable.objects.create(unidad=cls.lab, codigo='ALT-AREA-RV', nombre='Realidad virtual',
                                                    capacidad=8)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_el_menu_ofrece_agregar_en_cada_seccion(self):
        ficha = self.client.get(self.lab.get_absolute_url()).content.decode()
        for enlace in (reverse('nueva_area', args=[self.lab.slug]), reverse('nuevo_equipo', args=[self.lab.slug]),
                       reverse('editar_registro', args=[self.lab.slug, 'software', 'nuevo']),
                       reverse('editar_registro', args=[self.lab.slug, 'carpeta', 'nuevo']) + '?padre=s:1.4'):
            self.assertIn(enlace, ficha)
        self.client.force_login(self.visitante)
        self.assertNotIn(reverse('nueva_area', args=[self.lab.slug]), self.client.get(self.lab.get_absolute_url()).content.decode())
        self.assertEqual(self.client.get(reverse('nueva_area', args=[self.lab.slug])).status_code, 403)

    def test_una_nueva_area_nace_con_la_pagina_de_las_areas_y_texto_guia(self):
        respuesta = self.client.post(reverse('nueva_area', args=[self.lab.slug]),
                                     {'nombre': 'Metaverso', 'tipo': 'area', 'capacidad': 12}, HTTP_X_REQUESTED_WITH='fetch')
        area = EspacioReservable.objects.get(unidad=self.lab, nombre='Metaverso')
        self.assertEqual(respuesta.json(), {'ok': True, 'abrir': reverse('area_unidad', args=[self.lab.slug, area.codigo])})
        self.assertEqual(area.codigo, 'ALT-AREA-METAVERSO')
        ficha = FichaArea.objects.get(espacio=area)
        self.assertFalse(ficha.publicada)
        self.assertIn('Explique en dos o tres frases', ficha.que_es)
        pagina = self.client.get(reverse('area_unidad', args=[self.lab.slug, area.codigo]))
        self.assertContains(pagina, 'Explique en dos o tres frases')
        self.assertContains(pagina, 'data-editar-ficha')

    def test_un_equipo_nuevo_nace_con_su_ficha_y_no_se_publica_hasta_completarlo(self):
        respuesta = self.client.post(reverse('nuevo_equipo', args=[self.lab.slug]), {
            'nombre': 'Visor autónomo', 'area': self.area.pk, 'marca': 'Meta', 'modelo': 'Quest 3', 'cantidad': 2},
            HTTP_X_REQUESTED_WITH='fetch')
        unidades = list(UnidadEquipo.objects.filter(laboratorio=self.lab).order_by('codigo_unidad'))
        self.assertEqual([u.codigo_unidad for u in unidades], ['ALT-RV-01-01', 'ALT-RV-01-02'])
        self.assertEqual(respuesta.json()['abrir'], reverse('ficha_equipo_publica', args=[self.lab.slug, 'ALT-RV-01-01']))
        self.assertTrue(all(u.estado_unidad == 'no_disponible' and self.area in u.espacios_asociados.all() for u in unidades))
        self.assertIn('Describa en dos o tres frases', unidades[0].equipo.descripcion)
        self.assertFalse(UnidadEquipo.objects.publicos().filter(laboratorio=self.lab).exists())

    def test_procesos_y_carpetas_se_crean_desde_el_menu(self):
        producto = Producto.objects.create(unidad=self.lab, codigo='ALT-APP', nombre='Aplicación', unidad_medida='aplicación')
        url = reverse('editar_registro', args=[self.lab.slug, 'proceso', 'nuevo'])
        self.assertContains(self.client.get(url, {'fragmento': '1'}), 'name="registro-producto"')
        respuesta = self.client.post(url, {'registro-nombre': 'Desarrollo de una aplicación', 'registro-codigo': 'ALT-PRO-APP',
                                           'registro-producto': producto.pk, 'registro-cantidad_base': 1,
                                           'registro-unidad_base': 'aplicación', 'registro-rendimiento_esperado': 100,
                                           'registro-duracion_horas': 2},
                                     HTTP_X_REQUESTED_WITH='fetch')
        proceso = Receta.objects.get(codigo='ALT-PRO-APP')
        self.assertEqual(respuesta.json()['abrir'], reverse('proceso_laboratorio', args=[self.lab.slug, proceso.pk]))
        self.assertFalse(proceso.activa)
        carpetas = reverse('editar_registro', args=[self.lab.slug, 'carpeta', 'nuevo'])
        self.client.post(carpetas + '?padre=s:1.4', {'registro-nombre': 'Normas INEN', 'registro-visibilidad': 'publica'})
        normas = CarpetaRecurso.objects.get(unidad=self.lab, nombre='Normas INEN')
        self.assertEqual((normas.seccion_planta, normas.modulo_config.clave), ('1.4', 'informacion-general'))
        repetida = self.client.post(carpetas + '?padre=s:2.4', {'registro-nombre': 'Normas INEN', 'registro-visibilidad': 'publica'})
        self.assertContains(repetida, 'Ya hay una carpeta «Normas INEN»')
        comun = ModuloUnidad.objects.get(unidad=self.lab, clave='areas-equipos')
        self.assertEqual(self.client.get(carpetas + f'?padre=m:{comun.pk}').status_code, 404)
