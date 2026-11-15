"""Permisos, transiciones y trazabilidad de la remisión al decanato."""

from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from tests.historia import registro_anterior

from django.contrib import admin
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from apps.documentos.presentation.mejora_continua import generar_informe_de_mejora
from apps.documentos.presentation.mejora_seguimiento import contexto_mejora, tramitar_mejora
from apps.documentos.models.mejora import InformeMejora
from apps.recursos.models.recursos import Recurso
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_direccion_recibe_y_califica import ANIO, BaseDelExpediente


class CircuitoMejoraTests(BaseDelExpediente):
    databases = {'default', 'centros'} if settings.CENTROS_DB_ENABLED else {'default'}

    def informe(self, unidad=None):
        recurso = generar_informe_de_mejora(unidad or self.laboratorio, ANIO, 'A', self.coordinador)
        return recurso.informe_mejora

    def tramitar(self, informe, accion, usuario=None, **datos):
        return tramitar_mejora(informe.unidad, informe.pk, usuario or self.decano, accion, datos)

    def remitido(self):
        informe = self.informe()
        return self.tramitar(informe, 'remitir_mejora', self.direccion)

    def resuelto(self):
        informe = self.remitido()
        self.tramitar(informe, 'recibir_mejora')
        return self.tramitar(informe, 'decidir_mejora', decision='continuidad', motivo='Mejorar la atención.')

    def test_archivar_no_remite_y_receptor_no_abre_borrador(self):
        informe = self.informe()
        self.assertIsNone(informe.remitido_en)
        self.client.force_login(self.decano)
        self.assertEqual(self.client.get(reverse('recurso_unidad', args=[informe.recurso_id])).status_code, 404)
        self.assertEqual(contexto_mejora(self.laboratorio, ANIO, 'A', self.decano), {})

    def test_solo_direccion_remite_y_exige_destinatarios(self):
        informe = self.informe()
        with self.assertRaises(PermissionDenied):
            self.tramitar(informe, 'remitir_mejora', self.coordinador)
        self.decanato.receptores.clear()
        with self.assertRaises(ValidationError):
            self.tramitar(informe, 'remitir_mejora', self.direccion)
        informe.refresh_from_db()
        self.assertIsNone(informe.remitido_en)

    def test_sin_adscripcion_no_remite(self):
        informe = self.informe(self.suelto)
        with self.assertRaises(ValidationError):
            self.tramitar(informe, 'remitir_mejora', self.direccion)

    def test_antecedente_sin_causa_vigente_no_se_remite_ni_se_borra(self):
        informe = self.informe()
        recurso_id = informe.recurso_id
        auditorias = RegistroAuditoriaUnidad.objects.count()
        with patch('apps.documentos.presentation.mejora_continua.cumplimiento_del_periodo',
                   return_value={'requiere_mejora': False}):
            with self.assertRaisesMessage(ValidationError, 'antecedente'):
                self.tramitar(informe, 'remitir_mejora', self.direccion)
        informe.refresh_from_db()
        self.assertIsNone(informe.remitido_en)
        self.assertEqual(informe.destinatarios, [])
        self.assertEqual(informe.recurso_id, recurso_id)
        self.assertTrue(Recurso.objects.filter(pk=recurso_id).exists())
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), auditorias)

    def test_receptor_abre_remitido_y_revocacion_cierra_acceso_directo(self):
        informe = self.remitido()
        self.client.force_login(self.decano)
        respuesta = self.client.get(informe.recurso.archivo.url)
        self.assertEqual(respuesta.status_code, 200)
        b''.join(respuesta.streaming_content)
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            entidad='documentos.InformeMejora', accion='consultar', usuario=self.decano).exists())
        self.decanato.receptores.remove(self.decano)
        self.assertEqual(self.client.get(informe.recurso.archivo.url).status_code, 404)
        with self.assertRaises(PermissionDenied):
            self.tramitar(informe, 'recibir_mejora')

    def test_decision_requiere_recepcion_y_no_sobrescribe(self):
        informe = self.remitido()
        with self.assertRaises(ValidationError):
            self.tramitar(informe, 'decidir_mejora', decision='cierre', motivo='Sin uso.')
        self.tramitar(informe, 'recibir_mejora')
        self.tramitar(informe, 'decidir_mejora', decision='cierre', motivo='Sin uso.')
        with self.assertRaises(ValidationError):
            self.tramitar(informe, 'decidir_mejora', decision='continuidad', motivo='Cambiar.')
        self.laboratorio.refresh_from_db()
        self.assertTrue(self.laboratorio.activo)

    def test_remision_congela_version_y_destinatarios(self):
        informe = self.remitido()
        self.assertEqual(informe.destinatarios[0]['id'], self.decano.pk)
        with self.assertRaises(ValidationError):
            generar_informe_de_mejora(self.laboratorio, ANIO, 'A', self.coordinador)
        with self.assertRaises(ValidationError):
            informe.recurso.save()
        with self.assertRaises(ValidationError):
            self.tramitar(informe, 'remitir_mejora', self.direccion)

    def test_informe_de_otra_unidad_no_se_tramita(self):
        informe = self.remitido()
        with self.assertRaises(ValidationError):
            tramitar_mejora(self.suelto, informe.pk, self.direccion, 'remitir_mejora')

    def test_direccion_no_suplanta_al_destinatario(self):
        informe = self.remitido()
        with self.assertRaises(PermissionDenied):
            self.tramitar(informe, 'recibir_mejora', self.direccion)

    def test_fallo_auditoria_revierte_remision(self):
        informe = self.informe()
        with patch('apps.documentos.presentation.mejora_seguimiento.registrar_auditoria', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.tramitar(informe, 'remitir_mejora', self.direccion)
        informe.refresh_from_db()
        self.assertIsNone(informe.remitido_en)
        self.assertEqual(informe.destinatarios, [])

    def test_seguimiento_con_responsable_plazo_y_cierre_verificado(self):
        informe = self.resuelto()
        tarea = self.tramitar(informe, 'crear_accion_mejora', descripcion='Abrir nuevos horarios.',
                             responsable=str(self.coordinador.pk),
                             vence_el=(timezone.localdate() + timedelta(days=10)).isoformat())
        self.tramitar(informe, 'seguir_mejora', self.coordinador, tarea=tarea.pk, detalle='Horario propuesto.')
        with self.assertRaises(PermissionDenied):
            self.tramitar(informe, 'seguir_mejora', self.coordinador, tarea=tarea.pk, detalle='Listo.', cierre='1')
        self.tramitar(informe, 'seguir_mejora', tarea=tarea.pk, detalle='Horario verificado.', cierre='1')
        tarea.refresh_from_db()
        self.assertIsNotNone(tarea.cerrada_en)
        self.assertEqual(tarea.seguimientos.count(), 2)
        with self.assertRaises(ValidationError):
            self.tramitar(informe, 'seguir_mejora', tarea=tarea.pk, detalle='Cambiar cerrado.')
        contexto = contexto_mejora(self.laboratorio, ANIO, 'A', self.decano)
        self.assertIn(self.coordinador, contexto['responsables_mejora'])

    def test_no_asigna_a_receptor_sin_acceso_operativo(self):
        informe = self.resuelto()
        with self.assertRaises(ValidationError):
            self.tramitar(informe, 'crear_accion_mejora', descripcion='Acción',
                         responsable=str(self.decano.pk), vence_el=timezone.localdate().isoformat())

    def test_post_receptor_y_bandeja(self):
        informe = self.remitido()
        self.client.force_login(self.decano)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        respuesta = self.client.post(url, {'anio': ANIO, 'corte': 'A', 'informe': informe.pk,
                                         'accion': 'recibir_mejora'}, follow=True)
        self.assertContains(respuesta, 'Recepción registrada por')
        self.assertContains(respuesta, 'Registrar resolución')
        self.assertNotContains(respuesta, 'Regenerar con lo de hoy')
        request = RequestFactory().get('/')
        request.user = self.decano
        panel = admin.site._registry[InformeMejora]
        self.assertIn(informe, panel.get_queryset(request))
        self.assertFalse(panel.has_change_permission(request, informe))
        respuesta = self.client.get(reverse('admin:documentos_informemejora_changelist'))
        self.assertContains(respuesta, 'Abrir expediente')

    def test_cambio_de_adscripcion_retira_acceso(self):
        informe = self.remitido()
        self.laboratorio.adscrita_a = None
        self.laboratorio.save(update_fields=['adscrita_a'])
        with self.assertRaises(PermissionDenied):
            self.tramitar(informe, 'recibir_mejora')
        request = RequestFactory().get('/')
        request.user = self.decano
        self.assertNotIn(informe, admin.site._registry[InformeMejora].get_queryset(request))

    def test_admin_recursos_no_modifica_version_de_mejora(self):
        informe = self.remitido()
        request = RequestFactory().get('/')
        request.user = self.direccion
        self.assertNotIn(informe.recurso, admin.site._registry[Recurso].get_queryset(request))

    def test_migracion_vincula_historico_sin_fabricar_remision(self):
        informe = self.informe()
        recurso_id = informe.recurso_id
        informe.delete()
        migracion = import_module('apps.historial_modelos.migrations.0236_circuito_mejora')
        migracion.vincular_archivos(registro_anterior(), SimpleNamespace(connection=connection))
        migracion.vincular_archivos(registro_anterior(), SimpleNamespace(connection=connection))
        informe = InformeMejora.objects.get(recurso_id=recurso_id)
        self.assertEqual((informe.anio, informe.corte), (ANIO, 'A'))
        self.assertIsNone(informe.remitido_en)

    def test_el_informe_incluye_acciones_formales_y_avances(self):
        from apps.documentos.presentation.expediente_redaccion import _bloques_de_mejora_formal

        informe = self.resuelto()
        tarea = self.tramitar(informe, 'crear_accion_mejora', descripcion='Acción formal verificable',
                             responsable=str(self.coordinador.pk), vence_el=timezone.localdate().isoformat())
        self.tramitar(informe, 'seguir_mejora', self.coordinador,
                      tarea=tarea.pk, detalle='Avance registrado verificable')
        # Las acciones de mejora van en la sección 8 del informe semestral (documentos.0025).
        documento = self.documento(self.laboratorio, 'INFORME-SEMESTRAL', 'A')
        bloques = {b['titulo']: b for b in _bloques_de_mejora_formal(documento)}
        acciones = bloques['Acciones dispuestas por la Dirección']['filas']
        self.assertEqual([(fila[0], fila[1]) for fila in acciones], [(str(tarea.pk), 'Acción formal verificable')])
        avances = bloques['Seguimiento de esas acciones']['filas']
        self.assertEqual([(fila[0], fila[3]) for fila in avances], [(str(tarea.pk), 'Avance registrado verificable')])

    def test_el_anexo_anterior_de_mejora_incluye_acciones_formales_y_avances(self):
        from apps.documentos.models.expediente import DocumentoExigido
        from apps.documentos.presentation.expediente_redaccion import pdf_acciones_de_mejora

        # Retirado en documentos.0025: un expediente anterior que conserva el anexo sigue produciéndolo.
        DocumentoExigido.objects.filter(codigo='ACCIONES-MEJORA').update(activo=True)
        informe = self.resuelto()
        tarea = self.tramitar(informe, 'crear_accion_mejora', descripcion='Acción formal verificable',
                             responsable=str(self.coordinador.pk), vence_el=timezone.localdate().isoformat())
        self.tramitar(informe, 'seguir_mejora', self.coordinador,
                      tarea=tarea.pk, detalle='Avance registrado verificable')
        documento = self.documento(self.laboratorio, 'ACCIONES-MEJORA', 'A')
        with patch('apps.documentos.presentation.expediente_pdf.render_documento_pdf') as render:
            pdf_acciones_de_mejora(documento, timezone.localdate(), timezone.localdate())
        contenido = str(render.call_args.args[0])
        self.assertIn('Acción formal verificable', contenido)
        self.assertIn('Avance registrado verificable', contenido)
