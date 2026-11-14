"""Regresiones de procedencia, identidad e indicadores públicos de los centros."""
import importlib
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections, router
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import cidt
from apps.centros_id.contenidos import Contenidos
from apps.centros_id.models import Aliado, CentroID, DocumentoCentro, Indicador, Integrante, Proyecto, SolicitudCentro


class PublicacionInstitucionalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt, muestra=True).cargar()
        cls.gestor = get_user_model().objects.create_user('editor.centros', is_staff=True)
        cls.ajeno = get_user_model().objects.create_user('otra.persona')
        cls.centro.gestores.add(cls.gestor)

    def identidad(self):
        return self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'identidad']))

    def test_la_identidad_oficial_requiere_fuente_y_validacion(self):
        self.centro.adscripcion = 'Unidad de Investigación'
        self.centro.mision = 'Misión de prueba respaldada'
        self.centro.vision = 'Visión de prueba respaldada'
        self.centro.save()
        self.assertNotContains(self.identidad(), self.centro.mision)
        self.assertContains(self.identidad(), 'pendientes de validación institucional')
        with self.assertRaises(ValidationError):
            self.centro.validar_identidad(self.gestor)
        self.centro.fuente_identidad = 'Resolución institucional de prueba'
        self.centro.validar_identidad(self.gestor)
        self.assertContains(self.identidad(), self.centro.mision)
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.identidad_validada_por_id, self.gestor.pk)
        self.centro.mision = 'Misión corregida pendiente de revisión'
        self.centro.save(update_fields=['mision'])
        self.assertFalse(self.centro.identidad_validada)
        self.assertNotContains(self.identidad(), self.centro.mision)

    def test_estado_sin_respaldo_no_se_afirma_operativo(self):
        self.assertContains(self.identidad(), 'Estado pendiente de validación')
        self.centro.fuente_estado = 'Acta de puesta en operación'
        self.centro.validar_estado(self.gestor)
        self.assertContains(self.identidad(), 'Acta de puesta en operación')
        self.centro.estado = 'implementacion'
        self.centro.save(update_fields=['estado'])
        self.assertFalse(self.centro.estado_validado)
        self.assertContains(self.identidad(), 'Estado pendiente de validación')

    def test_solo_quien_gestiona_puede_validar(self):
        self.centro.fuente_estado = 'Acta'
        with self.assertRaises(ValidationError):
            self.centro.validar_estado(self.ajeno)
        muestra = self.centro.proyectos.first()
        muestra.fuente_validacion = 'Registro de proyecto real'
        with self.assertRaises(ValidationError):
            muestra.validar(self.ajeno)
        muestra.refresh_from_db()
        self.assertTrue(muestra.es_muestra)

    def test_las_muestras_no_aparecen_en_portada_ficha_ni_fragmentos(self):
        portada = self.client.get(reverse('centros_id'))
        self.assertNotContains(portada, 'cid-destacado')
        self.assertNotContains(portada, self.centro.proyectos.first().titulo)
        self.assertNotContains(portada, 'cid-ahora')
        for tipo, relacion in (('proyecto', 'proyectos'), ('persona', 'integrantes'), ('resultado', 'resultados'),
                               ('aliado', 'aliados'), ('caso', 'casos')):
            objeto = getattr(self.centro, relacion).first()
            url = reverse('fragmento_centro_id', args=[self.centro.slug, tipo, objeto.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.force_login(self.gestor)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.logout()
        c = Contenidos(self.centro)
        self.assertEqual(c.proyectos + c.resultados + c.integrantes + c.casos + c.aliados + c.convocatorias + c.novedades, [])
        self.assertTrue(all(not linea.retos and linea.retos_muestra for linea in c.lineas))

    def test_validar_una_muestra_exige_fuente_y_la_recarga_la_respeta(self):
        proyecto = self.centro.proyectos.first()
        with self.assertRaises(ValidationError):
            proyecto.validar(self.gestor)
        proyecto.titulo = 'Proyecto aprobado y verificado para la prueba'
        proyecto.fuente_validacion = 'Expediente institucional'
        proyecto.validar(self.gestor)
        Cargador(cidt, muestra=True, reescribir=True).cargar()
        proyecto.refresh_from_db()
        self.assertFalse(proyecto.es_muestra)
        self.assertEqual(proyecto.titulo, 'Proyecto aprobado y verificado para la prueba')
        self.assertEqual(Contenidos(self.centro).proyectos, [proyecto])

    def test_recargar_muestras_no_modifica_relaciones_de_un_registro_real(self):
        proyecto = self.centro.proyectos.first()
        proyecto.es_muestra = False
        proyecto.titulo = 'Registro existente preservado'
        proyecto.save()
        persona = Integrante.objects.create(centro=self.centro, nombre='Persona institucional', rol='investigador')
        proyecto.equipo.set([persona])
        Cargador(cidt, muestra=True, reescribir=True).cargar()
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.titulo, 'Registro existente preservado')
        self.assertEqual(list(proyecto.equipo.all()), [persona])

    def test_un_proyecto_real_no_divulga_relaciones_de_muestra(self):
        proyecto = Proyecto.objects.create(centro=self.centro, titulo='Proyecto real', resumen='Descripción',
                                           responsable=self.centro.integrantes.first())
        proyecto.aliados.add(self.centro.aliados.first())
        proyecto.equipo.add(self.centro.integrantes.first())
        pagina = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'proyecto', proyecto.pk]))
        self.assertEqual(pagina.status_code, 200)
        self.assertNotContains(pagina, proyecto.responsable.nombre)
        self.assertNotContains(pagina, self.centro.aliados.first().nombre)
        self.assertEqual(pagina.context['en_formacion'], 0)
        c = Contenidos(self.centro)
        self.assertIsNone(c.proyectos[0].responsable)
        self.assertEqual(next(i.valor for i in c.indicadores if i.calculo == 'proyectos_con_aliados'), 0)

    def test_un_aliado_real_no_muestra_proyectos_ni_casos_demostrativos(self):
        aliado = Aliado.objects.create(centro=self.centro, nombre='Aliado institucional')
        proyecto = self.centro.proyectos.first()
        proyecto.aliados.add(aliado)
        caso = self.centro.casos.first()
        caso.aliado = aliado
        caso.save()
        pagina = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'aliado', aliado.pk]))
        self.assertEqual(pagina.status_code, 200)
        self.assertNotContains(pagina, proyecto.titulo)
        self.assertNotContains(pagina, caso.titulo)

    def test_cero_y_dato_manual_pendiente_se_distinguen(self):
        pendiente = Indicador.objects.create(centro=self.centro, categoria='Impacto', nombre='Medición pendiente')
        cero = Indicador.objects.create(centro=self.centro, categoria='Impacto', nombre='Medición registrada',
                                       valor=0, actualizado=date(2026, 10, 1))
        c = Contenidos(self.centro)
        self.assertNotIn(pendiente, c.indicadores_medidos)
        self.assertIn(cero, c.indicadores_medidos)
        self.assertEqual(next(i.valor for i in c.indicadores if i.calculo == 'proyectos_activos'), 0)
        self.assertFalse(self.centro.indicadores.exclude(calculo='').filter(valor__isnull=False).exists())

    def test_solo_las_solicitudes_de_servicio_cuentan_como_servicios(self):
        for tipo in ('servicio', 'reto', 'uso', 'capacitacion', 'visita'):
            for estado in ('ejecucion', 'cerrada'):
                # Históricos importados: este caso verifica exclusivamente el universo del indicador.
                SolicitudCentro.objects.bulk_create([SolicitudCentro(centro=self.centro, usuario=self.ajeno,
                    tipo=tipo, estado=estado, titulo='Solicitud de prueba', problema='Necesidad de prueba')])
        c = Contenidos(self.centro)
        self.assertEqual(c.en_ejecucion, 1)
        cifra = next(f for f in c.cifras(9) if f['clave'] == 'atendidos')
        self.assertEqual(cifra['valor'], 1)
        self.assertIn('histórico', cifra['titulo'])

    def test_un_documento_aprobado_necesita_metadatos_y_el_borrador_no_es_publico(self):
        documento = DocumentoCentro(centro=self.centro, titulo='Resolución', tipo='creacion',
                                     estado_documental='aprobado', publico=True)
        with self.assertRaises(ValidationError):
            documento.full_clean()
        documento.emisor, documento.fecha, documento.fuente_validacion = 'Consejo', date(2026, 10, 1), 'Expediente'
        documento.full_clean()
        documento.save()
        borrador = DocumentoCentro.objects.create(centro=self.centro, titulo='Borrador', estado_documental='borrador')
        self.assertIn(documento, Contenidos(self.centro).documentos)
        self.assertNotIn(borrador, Contenidos(self.centro).documentos)
        self.assertIn(borrador, Contenidos(self.centro, self.gestor).documentos)

    def test_documentos_generados_son_borradores_y_no_sobrescriben_aprobados(self):
        cargador = Cargador(cidt, reescribir=True)
        with patch('apps.centros_id.documentos.pdf', return_value=b'%PDF-borrador'):
            cargador._documentos_generados(self.centro)
        documento = self.centro.documentos.first()
        self.assertFalse(documento.publico)
        self.assertEqual(documento.estado_documental, 'borrador')
        documento.estado_documental, documento.emisor, documento.fecha = 'aprobado', 'Consejo', date(2026, 10, 1)
        documento.fuente_validacion = 'Expediente'
        documento.validar(self.gestor)
        archivo = documento.archivo.name
        with patch('apps.centros_id.documentos.pdf', return_value=b'%PDF-reemplazo'):
            cargador._documentos_generados(self.centro)
        documento.refresh_from_db()
        self.assertEqual(documento.archivo.name, archivo)
        self.assertEqual(documento.estado_documental, 'aprobado')

    def test_migracion_identifica_firmas_originales_y_preserva_correcciones(self):
        self.centro.proyectos.update(es_muestra=False)
        original, corregido = list(self.centro.proyectos.all())[:2]
        corregido.resumen = 'Resumen corregido por el centro'
        corregido.save()
        ajeno = CentroID.objects.create(nombre='Otro centro', slug='otro-centro', area=self.centro.area, proposito='Prueba')
        copia = Proyecto.objects.get(pk=original.pk)
        copia.pk, copia.centro = None, ajeno
        copia.save()
        migracion = importlib.import_module('apps.centros_id.migrations.0010_clasifica_muestras_cidt')
        migracion.clasificar(apps, SimpleNamespace(connection=connections[router.db_for_write(CentroID)]))
        original.refresh_from_db()
        corregido.refresh_from_db()
        copia.refresh_from_db()
        self.assertTrue(original.es_muestra)
        self.assertFalse(corregido.es_muestra)
        self.assertFalse(copia.es_muestra)

    def test_la_marca_de_muestra_y_autoria_son_solo_lectura_en_admin(self):
        modelo_admin = admin.site._registry[Proyecto]
        request = RequestFactory().get('/')
        request.user = self.gestor
        campos = modelo_admin.get_readonly_fields(request)
        self.assertTrue({'es_muestra', 'validado_en', 'validado_por'} <= set(campos))
        self.assertNotIn('validar_contenido', modelo_admin.get_actions(request))
        request.user.is_superuser = True
        self.assertIn('validar_contenido', modelo_admin.get_actions(request))
