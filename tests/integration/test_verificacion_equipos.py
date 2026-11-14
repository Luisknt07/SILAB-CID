"""Lo que ve el público de los equipos y la verificación de que existen.

El público ve solo lo que está en servicio (disponible, en uso o prestado); lo dañado, obsoleto o no localizado
lo ve quien gestiona. Con la exigencia institucional activa, además, solo lo verificado. Verificar deja rastro en
la historia del equipo y solo lo hace quien gestiona los recursos de la unidad.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.gestion_unidades.presentation.conoce import equipos_de_la_unidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class VerificacionDeEquiposTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-verifica', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio que verifica', slug='lab-verifica', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        tipo = EquiposServicios.objects.create(codigo='VER-EQ-01', nombre='Osciloscopio de prueba')
        cls.bueno = UnidadEquipo.objects.create(codigo_unidad='VER-EQ-01-01', equipo=tipo, laboratorio=cls.unidad)
        cls.danado = UnidadEquipo.objects.create(codigo_unidad='VER-EQ-01-02', equipo=tipo, laboratorio=cls.unidad,
                                                 estado_unidad='dañado')
        cls.obsoleto = UnidadEquipo.objects.create(codigo_unidad='VER-EQ-01-03', equipo=tipo, laboratorio=cls.unidad,
                                                   estado_unidad='obsoleto')

    def test_el_publico_solo_ve_lo_que_esta_en_servicio(self):
        self.assertEqual(list(UnidadEquipo.objects.publicos()), [self.bueno])
        self.assertEqual(list(equipos_de_la_unidad(self.unidad)[0]), [self.bueno])
        ficha_danada = reverse('ficha_equipo_publica', args=[self.unidad.slug, self.danado.codigo_unidad])
        self.assertEqual(self.client.get(ficha_danada).status_code, 404)
        publica = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, self.bueno.codigo_unidad]))
        self.assertNotContains(publica, self.danado.codigo_unidad)
        self.client.force_login(self.gestor)
        gestion = self.client.get(ficha_danada)
        self.assertEqual(gestion.status_code, 200)
        self.assertContains(gestion, self.obsoleto.codigo_unidad)
        self.assertContains(gestion, 'Existencia por verificar')

    @override_settings(CITT_EXIGIR_EQUIPOS_VERIFICADOS=True)
    def test_con_la_exigencia_activa_solo_se_ve_lo_verificado(self):
        self.assertFalse(UnidadEquipo.objects.publicos().exists())
        self.assertFalse(self.bueno.es_publico)
        UnidadEquipo.objects.filter(pk=self.bueno.pk).update(existencia_verificada=True)
        self.assertEqual(list(UnidadEquipo.objects.publicos()), [self.bueno])

    def test_verificar_deja_rastro_y_solo_lo_hace_quien_gestiona(self):
        url = reverse('verificar_equipo', args=[self.unidad.slug, self.bueno.codigo_unidad])
        ajeno = get_user_model().objects.create_user('ajeno-verifica', password='clave')
        identificar(ajeno, tipo_usuario='estudiante')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.post(url, {'resultado': 'existe'}).status_code, 403)
        self.client.force_login(self.gestor)
        respuesta = self.client.post(url, {'resultado': 'existe', 'nota': 'Revisado en el inventario de octubre.'})
        self.assertRedirects(respuesta, reverse('ficha_equipo_publica', args=[self.unidad.slug, self.bueno.codigo_unidad]) + '#identidad',
                             fetch_redirect_response=False)
        self.bueno.refresh_from_db()
        self.assertTrue(self.bueno.existencia_verificada)
        self.assertEqual(self.bueno.existencia_verificada_por, self.gestor)
        self.assertIn('Existencia confirmada', EventoCicloVidaEquipo.objects.get(equipo=self.bueno, tipo='verificacion').descripcion)
        self.client.post(url, {'resultado': 'no_localizado'})
        self.bueno.refresh_from_db()
        self.assertEqual((self.bueno.estado_unidad, self.bueno.existencia_verificada), ('no_localizado', False))
        self.assertFalse(UnidadEquipo.objects.publicos().filter(pk=self.bueno.pk).exists())
