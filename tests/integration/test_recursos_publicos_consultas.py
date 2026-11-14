"""El árbol público mantiene consultas constantes y las mismas restricciones de acceso."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.formacion.presentation.recursos_publicos import _ContextoAccesoUnidad, _acceso_recurso, carpetas_publicables
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.models.mejora import InformeMejora
from apps.directorio_unidades.models.core import Unidad


class CarpetasPublicablesConsultasTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_superuser('gestor-arbol', 'arbol@example.org', None)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de consultas constantes', slug='laboratorio-consultas-constantes',
            dependencia='laboratorios', descripcion='Caso de prueba', fecha_inicio=date(2026, 1, 1),
        )
        cls.modulo = cls.unidad.modulos_contenido.get(clave='docencia-capacitacion')
        cls.carpeta = CarpetaRecurso.objects.create(
            unidad=cls.unidad, modulo_config=cls.modulo, nombre='Recursos de aprendizaje',
            seccion_planta='4.4', activa=True, visibilidad='publica',
        )

    def crear(self, cantidad, carpeta=None, inicio=0):
        return Recurso.objects.bulk_create([
            Recurso(unidad=self.unidad, carpeta=carpeta or self.carpeta, nombre=f'Recurso {inicio + i:03}',
                    url='https://www.upec.edu.ec/', activo=True, seguridad_verificada=True, visibilidad='publica')
            for i in range(cantidad)
        ])

    def medir(self, usuario=None):
        usuario = usuario or AnonymousUser()
        with CaptureQueriesContext(connection) as consultas:
            arbol = carpetas_publicables(self.unidad, usuario)
        return len(consultas), arbol

    def test_uno_y_treinta_recursos_utilizan_exactamente_cuatro_consultas(self):
        self.crear(1)
        pocas, arbol = self.medir()
        self.assertEqual(arbol['raices'][0].total_recursos, 1)
        self.crear(29, inicio=1)
        muchas, arbol = self.medir()
        self.assertEqual(arbol['raices'][0].total_recursos, 30)
        self.assertEqual(pocas, 4)
        self.assertEqual(muchas, pocas)

    def test_treinta_recursos_en_subcarpeta_heredan_restriccion_sin_consultas_por_archivo(self):
        self.carpeta.visibilidad = 'restringida'
        self.carpeta.save(update_fields=['visibilidad'])
        hija = CarpetaRecurso.objects.create(
            unidad=self.unidad, modulo_config=self.modulo, carpeta_padre=self.carpeta,
            nombre='Subcarpeta pública', seccion_planta='4.4', visibilidad='publica',
        )
        self.crear(30, carpeta=hija)
        consultas, arbol = self.medir()
        self.assertEqual(consultas, 4)
        self.assertEqual(arbol['raices'][0].total_recursos, 30)
        recursos = arbol['raices'][0].subcarpetas_publicas[0].recursos_publicos
        self.assertTrue(all(recurso.acceso_restringido for recurso in recursos))

    def test_ocultar_seccion_o_desactivar_superior_sigue_retirando_sus_recursos(self):
        self.crear(30)
        ajuste = AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='4.4', oculta=True)
        self.assertEqual(self.medir()[1]['raices'], [])
        ajuste.delete()
        self.carpeta.activa = False
        self.carpeta.save(update_fields=['activa'])
        self.assertEqual(self.medir()[1]['raices'], [])

    def test_informes_y_documentos_privados_no_se_publican_por_precargarlos(self):
        informe, documento, ordinario = self.crear(3)
        InformeMejora.objects.create(unidad=self.unidad, recurso=informe, anio=2026, corte='A')
        exigido = DocumentoExigido.objects.create(codigo='PRUEBA-ARBOL-INTERNO', nombre='Entrega interna', carpeta='planeacion')
        DocumentoExpediente.objects.create(unidad=self.unidad, recurso=documento, exigido=exigido,
                                            anio=2026, corte='A', estado='cargado')
        _, publico = self.medir()
        self.assertEqual([recurso.pk for recurso in publico['raices'][0].recursos_publicos], [ordinario.pk])
        _, privado = self.medir(self.gestor)
        self.assertEqual(privado['raices'][0].total_recursos, 3)

    def test_resolucion_validada_conserva_la_excepcion_publica_y_su_control_de_seguridad(self):
        recurso = self.crear(1)[0]
        exigido, _ = DocumentoExigido.objects.get_or_create(
            codigo='RESOLUCION-CREACION', defaults={'nombre': 'Resolución', 'carpeta': 'planeacion'})
        DocumentoExpediente.objects.create(unidad=self.unidad, recurso=recurso, exigido=exigido,
                                            anio=2026, estado='validado')
        self.assertEqual(self.medir()[1]['raices'][0].total_recursos, 1)
        Recurso.objects.filter(pk=recurso.pk).update(seguridad_verificada=False)
        self.assertEqual(self.medir()[1]['raices'], [])
        self.assertEqual(self.medir(self.gestor)[1]['raices'][0].total_recursos, 1)

    def test_contexto_no_se_reutiliza_entre_unidades_o_personas(self):
        recurso = self.crear(1)[0]
        persona = AnonymousUser()
        distinto = _ContextoAccesoUnidad(self.unidad.pk + 1, persona, True, frozenset())
        with self.assertRaises(ValueError):
            _acceso_recurso(recurso, persona, contexto=distinto)
        otra_persona = _ContextoAccesoUnidad(self.unidad.pk, AnonymousUser(), True, frozenset())
        with self.assertRaises(ValueError):
            _acceso_recurso(recurso, persona, contexto=otra_persona)

    def test_visibilidad_interna_y_archivos_sin_revision_siguen_ocultos(self):
        interno, sin_revision, publico = self.crear(3)
        Recurso.objects.filter(pk=interno.pk).update(visibilidad='interna')
        Recurso.objects.filter(pk=sin_revision.pk).update(seguridad_verificada=False)
        self.assertEqual([recurso.pk for recurso in self.medir()[1]['raices'][0].recursos_publicos], [publico.pk])
        self.assertEqual(self.medir(self.gestor)[1]['raices'][0].total_recursos, 2)

    def test_ficha_completa_no_suma_consultas_al_pasar_de_uno_a_treinta_recursos(self):
        self.crear(1)
        with patch('apps.gestion_unidades.presentation.detalle._registrar_visita'):
            # Calentar la configuración de presentación sin contar su inicialización.
            self.client.get(self.unidad.get_absolute_url())
            with CaptureQueriesContext(connection) as pocas:
                respuesta = self.client.get(self.unidad.get_absolute_url())
            self.assertEqual(respuesta.status_code, 200)
            self.crear(29, inicio=1)
            with CaptureQueriesContext(connection) as muchas:
                respuesta = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Recurso 029')
        self.assertEqual(len(muchas), len(pocas))
