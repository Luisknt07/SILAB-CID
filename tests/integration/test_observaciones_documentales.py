"""Los comentarios conservan su canal, autoría e historia sin alterar resultados."""
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.admin.expediente import DocumentoExpedienteAdmin
from apps.documentos.presentation.expediente import anotar_observacion
from apps.documentos.presentation.observaciones_documentales import (
    AUDITORIA_CORRECCION, contexto_observaciones, corregir_justificacion_tardia, identidad_comentario,
)
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_expediente_calidad import BaseDelExpediente


class ObservacionesDocumentalesLecturaTests(SimpleTestCase):
    def documento(self):
        return DocumentoExpediente(pk=10, unidad=Unidad(pk=1, slug='unidad-uno'),
            exigido=DocumentoExigido(pk=1, codigo='PLANIFICACION'), anio=2026, corte='B',
            version=1, estado='validado', observacion=',kl,llk', evaluacion=80,
            evaluacion_version=1, evaluacion_observacion='Evaluación histórica que debe conservarse.',
            evaluacion_debilidades='Falta una evidencia.', tardanza_motivo='cdcdccccccc')

    def test_modal_muestra_todos_los_canales_y_origen_sin_priorizar_uno_sobre_otro(self):
        d = self.documento()
        usuario = get_user_model()(pk=1, username='direccion', is_active=True, is_superuser=True)
        registro = SimpleNamespace(usuario=usuario, usuario_id=1, creado_en=timezone.now(),
            descripcion='anotar_observacion: PLANIFICACION', datos_anteriores={'observacion': ''},
            datos_nuevos={'observacion': ',kl,llk', 'version': 1})
        with patch.object(RegistroAuditoriaUnidad.objects, 'filter') as consulta, \
                patch('apps.documentos.presentation.observaciones_documentales.puede_operar_modulo_unidad', return_value=True):
            consulta.return_value.select_related.return_value.order_by.return_value = [registro]
            contexto = contexto_observaciones(d, usuario)
        self.assertEqual({c['campo'] for c in contexto['canales']},
            {'observacion', 'evaluacion_observacion', 'evaluacion_debilidades', 'tardanza_motivo'})
        self.assertEqual(contexto['canales'][0]['origen']['autor'], 'direccion')
        self.assertEqual({e['accion'] for e in contexto['editores']},
                         {'corregir_observacion', 'corregir_justificacion_tardia'})
        html = render_to_string('portal/pages/unidades/gestion/includes/observaciones_documentales.html',
            dict(documento=d, observaciones_documentales=contexto))
        for texto in (',kl,llk', 'cdcdccccccc', 'Evaluación histórica que debe conservarse.',
                      'Falta una evidencia.'):
            self.assertIn(texto, html)
        self.assertNotIn('Motivo de la corrección', html)
        self.assertIn('<summary>Historial</summary>', html)
        self.assertIn('type="hidden" name="motivo"', html)
        self.assertIn('name="huella_texto"', html)
        self.assertNotIn('name="evaluacion"', html)

    def test_edicion_del_texto_no_toca_calificacion_ni_estado(self):
        d = self.documento()
        identidad = identidad_comentario(d, 'observacion')
        usuario = SimpleNamespace(is_active=True, is_superuser=True)
        # Sin base de datos: la función de seguimiento de la cuenta se da por vigente.
        with patch.object(d, 'save') as guardar, \
                patch('apps.documentos.presentation.expediente.es_revisor_institucional', return_value=True), \
                patch('apps.documentos.presentation.observaciones_documentales.registrar_auditoria') as auditar:
            anotar_observacion.__wrapped__(d, usuario, 'Falta adjuntar el respaldo.',
                version=identidad['version'], recurso_id=identidad['recurso_id'], huella=identidad['huella'],
                huella_anterior=identidad['huella_texto'], motivo='Corregir texto escrito por error.')
        self.assertEqual(d.observacion, 'Falta adjuntar el respaldo.')
        self.assertEqual((d.estado, d.version, d.evaluacion, d.evaluacion_version), ('validado', 1, 80, 1))
        self.assertEqual(d.evaluacion_observacion, 'Evaluación histórica que debe conservarse.')
        guardar.assert_called_once_with(update_fields=['observacion', 'actualizado_en'])
        self.assertEqual(auditar.call_args.kwargs['anteriores']['observacion'], ',kl,llk')
        self.assertTrue(auditar.call_args.kwargs['nuevos']['sin_cambio_de_resultado'])

    def test_tokens_o_comentario_obsoleto_rechazan_correccion(self):
        for cambio in (dict(version='2'), dict(recurso_id='9'), dict(huella='a'*64),
                       dict(huella_anterior='b'*64)):
            with self.subTest(cambio=cambio):
                d = self.documento()
                identidad = identidad_comentario(d, 'observacion')
                datos = dict(version=identidad['version'], recurso_id=identidad['recurso_id'],
                    huella=identidad['huella'], huella_anterior=identidad['huella_texto'], motivo='Corrección.')
                datos.update(cambio)
                with patch.object(d, 'save') as guardar, self.assertRaises(ValidationError):
                    anotar_observacion.__wrapped__(d, SimpleNamespace(is_active=True, is_superuser=True),
                        'Texto nuevo.', **datos)
                guardar.assert_not_called()
                self.assertEqual(d.observacion, ',kl,llk')

    def test_la_justificacion_de_no_aplica_no_se_puede_vaciar(self):
        d = self.documento()
        d.estado, d.observacion = 'no_aplica', 'La unidad no genera estos residuos.'
        identidad = identidad_comentario(d, 'observacion')
        with patch.object(d, 'save') as guardar, \
                patch('apps.documentos.presentation.observaciones_documentales.registrar_auditoria') as auditar, \
                self.assertRaises(ValidationError):
            anotar_observacion.__wrapped__(d, SimpleNamespace(is_active=True, is_superuser=True), '',
                version=identidad['version'], recurso_id=identidad['recurso_id'], huella=identidad['huella'],
                huella_anterior=identidad['huella_texto'], motivo='Corrección de texto accidental.')
        self.assertEqual(d.observacion, 'La unidad no genera estos residuos.')
        guardar.assert_not_called()
        auditar.assert_not_called()

    def test_el_marcador_de_herencia_esta_reservado_al_sistema(self):
        for anterior, nuevo in ((',kl,llk', 'Heredado del año 2025. Documento vigente.'),
                ('Heredado del año 2025. Documento vigente.', 'Cambiar antecedente.')):
            with self.subTest(anterior=anterior):
                d = self.documento()
                d.observacion = anterior
                identidad = identidad_comentario(d, 'observacion')
                with patch.object(d, 'save') as guardar, \
                        patch('apps.documentos.presentation.observaciones_documentales.registrar_auditoria') as auditar, \
                        self.assertRaises(ValidationError):
                    anotar_observacion.__wrapped__(d, SimpleNamespace(is_active=True, is_superuser=True), nuevo,
                        version=identidad['version'], recurso_id=identidad['recurso_id'], huella=identidad['huella'],
                        huella_anterior=identidad['huella_texto'], motivo='Corrección de texto accidental.')
                self.assertEqual(d.observacion, anterior)
                guardar.assert_not_called()
                auditar.assert_not_called()

    def test_la_ficha_admin_es_consulta_y_conserva_acciones_de_lista(self):
        administracion = DocumentoExpedienteAdmin(DocumentoExpediente, admin.site)
        peticion = SimpleNamespace(user=SimpleNamespace(is_active=True, is_superuser=True))
        self.assertTrue(administracion.has_change_permission(peticion))
        self.assertFalse(administracion.has_change_permission(peticion, self.documento()))


class ObservacionesDocumentalesTransaccionTests(BaseDelExpediente):
    def preparado(self):
        d = self.documento('PLAN-COMPRAS-ANUAL')
        d.observacion, d.tardanza_motivo = ',kl,llk', 'cdcdccccccc'
        d.evaluacion, d.evaluacion_version = 80, d.version
        d.evaluacion_observacion = 'Conclusión histórica conservada.'
        d.save()
        return d

    def datos(self, d, campo='observacion'):
        identidad = identidad_comentario(d, campo)
        return dict(version=identidad['version'], recurso_id=identidad['recurso_id'],
            huella=identidad['huella'], huella_anterior=identidad['huella_texto'],
            motivo='Corrección de texto accidental.')

    def test_ambos_canales_usan_auditoria_y_conservan_notas_plazos_y_solicitud(self):
        d = self.preparado()
        antes = (d.estado, d.version, d.evaluacion, d.evaluacion_version, d.evaluacion_observacion,
                 d.tardanza_pedida_en, d.tardanza_habilitada_en, d.correccion_hasta)
        anotar_observacion(d, self.direccion, 'Completar el fundamento.', **self.datos(d))
        corregir_justificacion_tardia(d, self.coordinador, 'La cotización se recibió después del plazo.',
                                      **self.datos(d, 'tardanza_motivo'))
        d.refresh_from_db()
        self.assertEqual((d.estado, d.version, d.evaluacion, d.evaluacion_version, d.evaluacion_observacion,
            d.tardanza_pedida_en, d.tardanza_habilitada_en, d.correccion_hasta), antes)
        registros = RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad, objeto_id=str(d.pk),
                                                           descripcion=AUDITORIA_CORRECCION)
        self.assertEqual(registros.count(), 2)
        self.assertEqual({r.datos_nuevos['canal'] for r in registros}, {'observacion', 'tardanza_motivo'})

    def test_operador_no_edita_observacion_de_direccion(self):
        d = self.preparado()
        with self.assertRaises(ValidationError):
            anotar_observacion(d, self.coordinador, 'Cambio ajeno.', **self.datos(d))
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(reverse('gestion_expediente_unidad', args=[self.unidad.slug]),
            dict(accion='corregir_observacion', documento=d.pk, texto='Cambio ajeno.', **self.datos(d)))
        self.assertEqual(respuesta.status_code, 403)
        d.refresh_from_db()
        self.assertEqual(d.observacion, ',kl,llk')

    def test_el_post_generico_admin_no_modifica_el_documento_ni_su_historia(self):
        d = self.preparado()
        self.client.force_login(self.direccion)
        campos = ('observacion', 'tardanza_motivo', 'estado', 'version', 'evaluacion',
                  'evaluacion_version', 'evaluacion_observacion', 'actualizado_en')
        antes = tuple(getattr(d, campo) for campo in campos)
        historial = RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad,
            entidad=d._meta.label, objeto_id=str(d.pk))
        cantidad = historial.count()
        respuesta = self.client.post(reverse(f'admin:{d._meta.app_label}_{d._meta.model_name}_change',
            args=[d.pk]), dict(observacion='Cambio fuera del circuito auditado.', _save='Guardar'))
        self.assertEqual(respuesta.status_code, 403)
        d.refresh_from_db()
        self.assertEqual(tuple(getattr(d, campo) for campo in campos), antes)
        self.assertEqual(historial.count(), cantidad)

    def test_fallo_de_auditoria_revierte_ambos_textos(self):
        for campo, funcion, actor in (('observacion', anotar_observacion, self.direccion),
                ('tardanza_motivo', corregir_justificacion_tardia, self.coordinador)):
            with self.subTest(campo=campo):
                d = self.preparado()
                antes = getattr(d, campo)
                with patch('apps.documentos.presentation.observaciones_documentales.registrar_auditoria',
                           side_effect=RuntimeError('Fallo de auditoría')), self.assertRaises(RuntimeError):
                    funcion(d, actor, 'Corrección que no debe persistir.', **self.datos(d, campo))
                d.refresh_from_db()
                self.assertEqual(getattr(d, campo), antes)

    def test_director_y_unidad_abren_los_mismos_canales_en_modal(self):
        d = self.preparado()
        self.client.force_login(self.direccion)
        respuesta = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
            dict(unidad=self.unidad.slug, anio=d.anio, corte='B', revisar=d.pk, vista='observaciones'))
        self.assertEqual(respuesta.status_code, 200)
        for texto in (',kl,llk', 'cdcdccccccc', 'Conclusión histórica conservada.', 'corregir_observacion'):
            self.assertContains(respuesta, texto)
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]),
            dict(anio=d.anio, corte='B', gestionar=d.pk, vista='observaciones', fragment='1'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'corregir_justificacion_tardia')
        self.assertNotContains(respuesta, 'name="accion" value="corregir_observacion"')
        for texto in (',kl,llk', 'cdcdccccccc', 'Conclusión histórica conservada.'):
            self.assertContains(respuesta, texto)
