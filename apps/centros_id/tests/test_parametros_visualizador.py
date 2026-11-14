"""Entradas numéricas inválidas responden 404; las referencias válidas se conservan."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.centros_id.models import (
    CarpetaCentro, CentroID, Componente, EquipoCentro, Proyecto, Resultado, Zona,
)


class ParametrosVisualizadorTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}
    invalidos = ('²', '١', '9' * 5000, '1' * 19, '-1', 'texto')

    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroID.objects.create(nombre='Parámetros', slug='centro-parametros', proposito='Investigar')
        cls.gestor = get_user_model().objects.create_user('gestor.parametros')
        cls.centro.gestores.add(cls.gestor)
        cls.proyecto = Proyecto.objects.create(centro=cls.centro, titulo='Proyecto válido', resumen='Resumen')
        cls.desarrollo = Resultado.objects.create(centro=cls.centro, titulo='Desarrollo válido', tipo='prototipo', anio=2026)
        cls.area = Componente.objects.create(centro=cls.centro, codigo='area', nombre='Área', estado='operativa')
        cls.equipo = EquipoCentro.objects.create(componente=cls.area, nombre='Equipo válido', reservable=True,
            es_activo_individual=True, codigo='EQ-1', cantidad=1)
        cls.zona = Zona.objects.create(centro=cls.centro, codigo='Z-1', nombre='Zona válida', nivel='Planta baja',
            area_m2=20, reservable=True, estado_acceso='disponible', aforo=4)
        cls.carpeta = CarpetaCentro.objects.create(centro=cls.centro, pestana='el-centro', nombre='Carpeta pública')

    def test_abrir_no_convierte_unicode_ni_enteros_sin_limite(self):
        direccion = reverse('seccion_centro_id', args=[self.centro.slug, 'presentacion'])
        for valor in self.invalidos:
            with self.subTest(valor=valor[:20]):
                self.assertEqual(self.client.get(direccion, {'abrir': valor}).status_code, 404)
        respuesta = self.client.get(direccion, {'abrir': str(self.proyecto.pk)})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['abrir'], self.proyecto.pk)

    def test_carpeta_valida_recurso_antes_de_convertir(self):
        direccion = reverse('carpeta_centro_id', args=[self.centro.slug, self.carpeta.pk])
        for valor in self.invalidos:
            with self.subTest(valor=valor[:20]):
                self.assertEqual(self.client.get(direccion, {'recurso': valor}).status_code, 404)
        respuesta = self.client.get(direccion, {'recurso': '42'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['abrir'], 42)

    def test_solicitar_rechaza_ids_invalidos_de_las_cuatro_referencias(self):
        direccion = reverse('solicitar_centro_id', args=[self.centro.slug])
        for campo in ('proyecto', 'desarrollo', 'equipo', 'zona'):
            for valor in self.invalidos:
                with self.subTest(campo=campo, valor=valor[:20]):
                    self.assertEqual(self.client.get(direccion, {campo: valor}).status_code, 404)

    def test_solicitar_con_referencia_valida_conserva_el_formulario_inicial(self):
        self.client.force_login(self.gestor)
        direccion = reverse('solicitar_centro_id', args=[self.centro.slug])
        for campo, objeto in (('proyecto', self.proyecto), ('desarrollo', self.desarrollo),
                              ('equipo', self.equipo), ('zona', self.zona)):
            with self.subTest(campo=campo):
                respuesta = self.client.get(direccion, {campo: objeto.pk, 'tipo': 'uso' if campo in ('equipo', 'zona') else 'reto'})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context['formulario'].initial[campo], objeto.pk)

    def test_editar_rechaza_ids_invalidos_y_abre_el_registro_valido(self):
        self.client.force_login(self.gestor)
        direccion = reverse('gestion_centro_id', args=[self.centro.slug])
        for valor in self.invalidos:
            with self.subTest(valor=valor[:20]):
                self.assertEqual(self.client.get(direccion, {'panel': 'investigacion', 'tipo': 'proyectos', 'editar': valor}).status_code, 404)
        respuesta = self.client.get(direccion, {'panel': 'investigacion', 'tipo': 'proyectos', 'editar': self.proyecto.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['formulario'].instance.pk, self.proyecto.pk)
