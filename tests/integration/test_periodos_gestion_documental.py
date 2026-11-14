"""Gestión natural, calendario docente separado y documentos históricos estables."""
from datetime import date
from importlib import import_module
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch, Mock

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import connection
from django.test import TestCase, SimpleTestCase, override_settings

from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.evaluacion_cierre import VERSION, lectura_cierre, congelar_cierre
from apps.documentos.presentation.evaluacion_cierre import detalle_anexo
from apps.documentos.presentation.expediente import (
    construir_expediente, cortes_del_anio, cortes_academicos_del_anio,
    leer_expediente, tramo_del_documento, instantanea_periodo, _exigir_cierre_concluido,
)
from apps.documentos.presentation.expediente_archivos import metadatos_documentales
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import Recurso
from tests.integration.utiles import pdf_legible_prueba


class MigracionAmbitosHistoricosTests(SimpleTestCase):
    def setUp(self):
        self.migracion = import_module('apps.documentos.migrations.0010_tramos_gestion')
        self.configuracion = SimpleNamespace(ACADEMIC_CALENDAR={'ambitos_operacion': ['carreras_centros']},
            INSTITUTION_IDENTITY={'siglas': 'UPEC'}, PRODUCT_IDENTITY={'codigo': 'SLCID'})

    def consulta(self, revision=None):
        manager = Mock()
        manager.using.return_value = manager
        manager.select_related.return_value = manager
        manager.filter.return_value = manager
        manager.first.return_value = (SimpleNamespace(revision_id=1, revision=revision) if revision else None)
        registro = SimpleNamespace(get_model=Mock(return_value=SimpleNamespace(objects=manager)))
        return registro, manager

    def revision(self, contenido=None, **extra):
        valores = dict(estado='publicada', institucion_codigo='UPEC', producto_codigo='SLCID',
                       contenido=contenido if contenido is not None else {'ambitos_operacion': ['extension_operativa']})
        valores.update(extra)
        return SimpleNamespace(**valores)

    def test_publicacion_historica_prevalece_sobre_default_sin_importar_proveedor_actual(self):
        registro, manager = self.consulta(self.revision())
        self.assertEqual(self.migracion._ambitos_historicos(registro, 'historica', self.configuracion),
                         ('extension_operativa',))
        manager.using.assert_called_once_with('historica')
        registro.get_model.assert_called_once_with('configuracion_institucional', 'PublicacionPoliticaCalendario')

    def test_falta_de_publicacion_usa_fallback_de_despliegue(self):
        registro, _ = self.consulta()
        self.assertEqual(self.migracion._ambitos_historicos(registro, 'default', self.configuracion),
                         ('carreras_centros',))

    def test_campo_no_guardado_en_publicacion_antigua_usa_fallback(self):
        registro, _ = self.consulta(self.revision(contenido={}))
        self.assertEqual(self.migracion._ambitos_historicos(registro, 'default', self.configuracion),
                         ('carreras_centros',))

    def test_ambitos_vacios_explicitamente_no_se_sustituyen_por_otros(self):
        registro, _ = self.consulta(self.revision(contenido={'ambitos_operacion': []}))
        self.assertEqual(self.migracion._ambitos_historicos(registro, 'default', self.configuracion), ())

    def test_publicacion_invalida_o_ajena_no_congela_otro_calendario_silenciosamente(self):
        for datos in (dict(estado='borrador'), dict(institucion_codigo='OTRA'), dict(producto_codigo='OTRO'),
                      dict(contenido={'ambitos_operacion': 'extension_operativa'}),
                      dict(contenido={'ambitos_operacion': [1]})):
            with self.subTest(datos=datos):
                registro, _ = self.consulta(self.revision(**datos))
                with self.assertRaises(RuntimeError):
                    self.migracion._ambitos_historicos(registro, 'default', self.configuracion)

    def test_router_centros_impide_cualquier_consulta_de_documentos_en_otra_base(self):
        registro = SimpleNamespace(get_model=Mock(side_effect=AssertionError('No debe consultar esta base')))
        editor = SimpleNamespace(connection=SimpleNamespace(alias='centros'))
        with patch.object(self.migracion.router, 'allow_migrate', return_value=False):
            self.migracion.conservar_tramos(registro, editor)
        registro.get_model.assert_not_called()


class PeriodosGestionDocumentalTests(TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-periodo-gestion-')
        self.addCleanup(carpeta.cleanup)
        ajuste = override_settings(MEDIA_ROOT=carpeta.name)
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        asegurar_catalogo()
        self.actor = get_user_model().objects.create_superuser('gestion-natural-direccion', password=None)
        self.unidad = Unidad.objects.create(nombre='Laboratorio de alcances', slug='gestion-natural',
            dependencia='laboratorios', administrador=self.actor, fecha_inicio=date(2020, 1, 1))
        self.periodo = PeriodoAcademico.objects.create(codigo='2026-B-GESTION-QA', anio_referencia=2026,
            ciclo='B', tipo='ordinario', ambito='carreras_centros', estado='publicado')
        self.calendario = VersionCalendarioAcademico.objects.create(periodo=self.periodo, numero=1,
            fecha_inicio_clases=date(2026, 8, 17), fecha_fin_clases=date(2026, 12, 8),
            fecha_fin_periodo=date(2026, 12, 8), vigente=True)

    def documentos(self):
        return construir_expediente(self.unidad, 2026, hoy=date(2026, 10, 18))

    def documento(self, codigo='INFORME-SEMESTRAL', corte='B'):
        return next(d for d in self.documentos() if d.exigido.codigo == codigo and d.corte == corte)

    def test_gestion_abarca_enero_junio_y_julio_diciembre_aunque_haya_calendario_docente(self):
        self.assertEqual(cortes_del_anio(2026), {
            'A': (date(2026, 1, 1), date(2026, 6, 30)),
            'B': (date(2026, 7, 1), date(2026, 12, 31))})
        self.assertEqual(cortes_academicos_del_anio(2026)['B'],
                         (date(2026, 8, 17), date(2026, 12, 8)))

    def test_nuevos_documentos_y_anexos_conservan_fechas_naturales(self):
        for d in self.documentos():
            if d.corte == 'B' and d.periodicidad_documental == 'semestral':
                self.assertEqual(tramo_del_documento(d), (date(2026, 7, 1), date(2026, 12, 31)))
                self.assertEqual((d.tramo_inicio, d.tramo_fin), tramo_del_documento(d))
                self.assertEqual(d.marco_periodo, 'gestion_v1')
        compra = self.documento('PLAN-COMPRAS-ANUAL', '')
        self.assertEqual(tramo_del_documento(compra), (date(2026, 1, 1), date(2026, 12, 31)))

    def test_apertura_y_entrega_de_cierre_separan_quince_dias_antes_y_despues(self):
        a = self.documento(corte='A')
        b = self.documento(corte='B')
        self.assertEqual((a.abre_el, a.vence_el), (date(2026, 6, 15), date(2026, 7, 15)))
        self.assertEqual((b.abre_el, b.vence_el), (date(2026, 12, 16), date(2027, 1, 15)))
        self.assertEqual((a.exigido.plazo_regla, a.exigido.plazo_dias), ('cierre', 15))

    def test_la_regla_fin_personalizada_conserva_semantica_anterior(self):
        legado = DocumentoExigido(codigo='LEGADO', plazo_regla='fin', plazo_dias=3, apertura_dias=15)
        self.assertEqual(legado.vence(date(2026, 7, 1), date(2026, 12, 31)), date(2026, 12, 28))
        self.assertEqual(legado.abre(date(2026, 7, 1), date(2026, 12, 31)), date(2026, 12, 13))

    def test_reforma_docente_no_cambia_alcance_ni_plazos_de_gestion_guardados(self):
        d = self.documento()
        anterior = (d.tramo_inicio, d.tramo_fin, d.abre_el, d.vence_el)
        self.calendario.fecha_inicio_clases = date(2026, 9, 1)
        self.calendario.fecha_fin_clases = date(2026, 12, 20)
        self.calendario.fecha_fin_periodo = date(2026, 12, 22)
        self.calendario.save()
        self.documentos()
        d.refresh_from_db()
        self.assertEqual(anterior, (d.tramo_inicio, d.tramo_fin, d.abre_el, d.vence_el))

    def test_proyecciones_sin_filas_no_escriben_y_tambien_usan_gestion(self):
        antes = DocumentoExpediente.objects.count()
        proyectados = leer_expediente(self.unidad, 2027, date(2026, 10, 18))
        self.assertEqual(DocumentoExpediente.objects.count(), antes)
        b = next(d for d in proyectados if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')
        self.assertIsNone(b.pk)
        self.assertEqual(tramo_del_documento(b), (date(2027, 7, 1), date(2027, 12, 31)))
        self.assertEqual(b.vence_el, date(2028, 1, 15))

    def test_snapshot_legado_permanece_aunque_se_construya_nuevo_expediente(self):
        d = self.documento()
        d.tramo_inicio, d.tramo_fin = date(2026, 8, 17), date(2026, 12, 8)
        d.marco_periodo = 'academico_legacy'
        d.abre_el, d.vence_el = date(2026, 11, 23), date(2026, 12, 8)
        d.save()
        self.documentos()
        d.refresh_from_db()
        self.assertEqual(tramo_del_documento(d), (date(2026, 8, 17), date(2026, 12, 8)))
        self.assertEqual((d.abre_el, d.vence_el), (date(2026, 11, 23), date(2026, 12, 8)))

    def test_migracion_conserva_pdf_notas_y_ventanas_con_su_alcance_original(self):
        d = self.documento()
        archivo = pdf_legible_prueba('Archivo histórico: 17/08/2026 al 08/12/2026.')
        r = Recurso.objects.create(unidad=self.unidad, nombre='Cierre histórico',
            descripcion='Informe semestral del 17/08/2026 al 08/12/2026, redactado con el editor guiado.',
            archivo=ContentFile(archivo, name='historico.pdf'))
        d.recurso, d.version, d.estado = r, 2, 'validado'
        d.evaluacion, d.evaluacion_version = 74, 2
        d.abre_el, d.vence_el = date(2026, 11, 23), date(2026, 12, 8)
        d.save()
        migracion = import_module('apps.documentos.migrations.0010_tramos_gestion')
        migracion.conservar_tramos(apps, SimpleNamespace(connection=connection))
        d.refresh_from_db()
        r.refresh_from_db()
        self.assertEqual((d.estado, d.version, d.evaluacion, d.evaluacion_version), ('validado', 2, 74, 2))
        self.assertEqual(tramo_del_documento(d), (date(2026, 8, 17), date(2026, 12, 8)))
        self.assertEqual((d.abre_el, d.vence_el), (date(2026, 11, 23), date(2026, 12, 8)))
        self.assertEqual(d.marco_periodo, 'academico_legacy')
        with r.archivo.open('rb') as contenido:
            self.assertEqual(contenido.read(), archivo)

    def test_cierre_archivado_no_se_recalcula_con_rango_nuevo(self):
        d = self.documento()
        d.estado, d.version = 'validado', 1
        d.marco_periodo = 'academico_legacy'
        d.tramo_inicio, d.tramo_fin = date(2026, 8, 17), date(2026, 12, 8)
        d.save()
        captura = dict(metodo=VERSION, version=1, recurso=None, nota=63, congelado=True,
                       filas=[], anexos=[])
        RegistroAuditoriaUnidad.objects.create(unidad=self.unidad, usuario=self.actor,
            entidad=d._meta.label, objeto_id=str(d.pk), accion='enviar', descripcion='Cierre histórico',
            datos_nuevos=captura)
        self.assertEqual(lectura_cierre(d), captura)

    def test_informe_puede_prepararse_antes_pero_no_cerrarse_definitivamente(self):
        d = self.documento()
        for hoy in (date(2026, 12, 16), date(2026, 12, 31)):
            with self.subTest(hoy=hoy), patch('django.utils.timezone.localdate', return_value=hoy):
                with self.assertRaisesMessage(ValidationError, 'informe provisional'):
                    _exigir_cierre_concluido(d)
                with self.assertRaises(ValidationError):
                    congelar_cierre(d, self.actor)
        with patch('django.utils.timezone.localdate', return_value=date(2027, 1, 1)):
            _exigir_cierre_concluido(d)

    def test_metadatos_nuevos_conservan_rango_y_metadatos_legados_no_se_reescriben(self):
        d = self.documento()
        compuesto = dict(documento=d, tipo='informe', tramo=tramo_del_documento(d), secciones=[], firmas=[])
        nuevo = metadatos_documentales(compuesto)
        self.assertEqual(nuevo['periodo_documental'], instantanea_periodo(d))
        d.marco_periodo = 'academico_legacy'
        legado = metadatos_documentales(compuesto)
        self.assertNotIn('periodo_documental', legado)
        self.assertEqual({k: v for k, v in nuevo.items() if k != 'periodo_documental'}, legado)

    def test_anexo_uso_conserva_horas_comprometidas_sin_inventarlas_en_legacy(self):
        base = dict(codigo='USO', nombre='Cobertura de registros', exigible=True, porcentaje=100, pendiente=False)
        horas = dict(codigo='USO-EFECTIVO', nombre='Horas efectivas de atención', exigible=True, porcentaje=50, pendiente=False)
        nuevo = detalle_anexo('REGISTRO-USO', dict(catalogo=[base, horas]))
        legado = detalle_anexo('REGISTRO-USO', dict(catalogo=[base]))
        self.assertEqual([f['codigo'] for f in nuevo], ['USO', 'USO-EFECTIVO'])
        self.assertEqual([f['codigo'] for f in legado], ['USO'])
