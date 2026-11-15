"""Dirección devuelve con fecha; la unidad corrige dentro de esa apertura."""
from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import timezone

from apps.documentos.models.expediente import DocumentoExigido
from apps.documentos.presentation.conformidad_permanente import APROBAR, REVOCAR, aprobar_permanente
from apps.documentos.presentation.expediente import (
    habilitar_entrega_tardia, observar_documento, solicitar_entrega_tardia, validar_documento,
)
from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
from apps.documentos.presentation.cumplimiento import cumplimiento_de_unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_direccion_recibe_y_califica import ANIO, BaseDelExpediente
from tests.integration.utiles import (
    cargar_documento_revisado as cargar_documento,
    correspondencia_revisada,
    pdf_legible_prueba,
)


class FechasCorreccionTests(BaseDelExpediente):
    def entrega(self):
        d = self.documento(self.laboratorio, 'RESOLUCION-CREACION', '')
        self.abrir_plazo(d)
        cargar_documento(d, SimpleUploadedFile('resolucion.pdf', pdf_legible_prueba()), self.coordinador)
        validar_documento(d, self.coordinador)
        return d

    def test_fecha_futura_obligatoria_y_rechazo_sin_cambios(self):
        d = self.entrega()
        for valor in (None, '', 'incorrecta', '2026-02-31T12:00', timezone.now() - timedelta(minutes=1)):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                observar_documento(d, self.direccion, 'Completar evidencia', hasta=valor)
            d.refresh_from_db()
            self.assertEqual(d.estado, 'validado')
            self.assertIsNone(d.correccion_hasta)

    def test_solo_direccion_devuelve_y_el_receptor_no_asigna_fechas(self):
        d = self.entrega()
        for usuario in (self.coordinador, self.decano):
            with self.assertRaises(ValidationError):
                observar_documento(d, usuario, 'Cambiar', hasta=timezone.now() + timedelta(days=2))

    def test_devolver_audita_fecha_y_nota_sin_cambiar_plazo_institucional(self):
        d = self.entrega()
        aprobar_permanente(d, self.direccion, d.version, d.recurso.hash_sha256,
                           confirmado=True, declaracion_correspondencia=correspondencia_revisada(d))
        # Aprobado: es de cumplimiento obligatorio, aceptado y sin porcentaje.
        self.assertIsNone(d.nota)
        self.assertIs(d.cumple, True)
        self.assertIsNone(d.evaluacion)
        original = d.plazo_original
        hasta = timezone.now() + timedelta(days=2)
        observar_documento(d, self.direccion, 'Completar evidencia', hasta=hasta)
        self.assertEqual(d.correccion_hasta, hasta)
        self.assertEqual(d.plazo_original, original)
        self.assertIsNone(d.nota)
        self.assertIsNone(d.recibido_en)
        self.assertEqual(resumen_de_entrega(d)['tipo_plazo'], 'Corrección')
        r = RegistroAuditoriaUnidad.objects.filter(objeto_id=str(d.pk),
            descripcion__startswith='observar_documento:').latest('pk')
        self.assertIsNone(r.datos_anteriores['evaluacion'])
        self.assertTrue(r.datos_nuevos['correccion_hasta'])
        decisiones = RegistroAuditoriaUnidad.objects.filter(
            objeto_id=str(d.pk), descripcion__in=(APROBAR, REVOCAR)).order_by('pk')
        self.assertEqual([registro.datos_nuevos['estado'] for registro in decisiones],
                         ['aprobado', 'revocado'])
        self.assertTrue(all(registro.usuario_id == self.direccion.pk for registro in decisiones))

    def test_correccion_abre_tras_plazo_original_y_conserva_puntualidad_al_reenviar(self):
        d = self.entrega()
        d.vence_el = timezone.localdate() - timedelta(days=1)
        d.save(update_fields=['vence_el'])
        hasta = timezone.now() + timedelta(hours=2)
        observar_documento(d, self.direccion, 'Completar evidencia', hasta=hasta)
        self.assertTrue(d.entrega_abierta)
        version = d.version
        cargar_documento(d, SimpleUploadedFile('corregida.pdf', pdf_legible_prueba('Documento corregido de prueba.')), self.coordinador)
        self.assertEqual(d.version, version + 1)
        validar_documento(d, self.coordinador)
        self.assertFalse(d.entregado_tarde)
        self.assertEqual(d.correccion_hasta, hasta)

    def test_correccion_vencida_bloquea_envio_aunque_el_archivo_ya_fue_cargado(self):
        d = self.entrega()
        hasta = timezone.now() + timedelta(hours=2)
        observar_documento(d, self.direccion, 'Completar evidencia', hasta=hasta)
        cargar_documento(d, SimpleUploadedFile('corregida.pdf', pdf_legible_prueba('Documento corregido de prueba.')), self.coordinador)
        with patch('apps.documentos.models.expediente.timezone.now', return_value=hasta + timedelta(seconds=1)):
            self.assertFalse(d.entrega_abierta)
            with self.assertRaisesMessage(ValidationError, 'corrección venció'):
                validar_documento(d, self.coordinador)
            with self.assertRaises(ValidationError):
                cargar_documento(d, SimpleUploadedFile('otra.pdf', pdf_legible_prueba('Otra corrección de prueba.')), self.coordinador)

    def test_correccion_no_elimina_tardanza_previa_ni_reutiliza_solicitudes(self):
        d = self.entrega()
        d.entregado_tarde = True
        d.tardanza_pedida_en = timezone.now() - timedelta(hours=1)
        d.save(update_fields=['entregado_tarde', 'tardanza_pedida_en'])
        observar_documento(d, self.direccion, 'Completar evidencia', hasta=timezone.now() + timedelta(hours=2))
        self.assertFalse(d.solicitud_reapertura_pendiente)
        cargar_documento(d, SimpleUploadedFile('corregida.pdf', pdf_legible_prueba('Documento corregido de prueba.')), self.coordinador)
        validar_documento(d, self.coordinador)
        self.assertTrue(d.entregado_tarde)

    def test_correccion_vencida_admite_reapertura_justificada_sin_ultimatum_nuevo(self):
        d = self.entrega()
        hasta = timezone.now() + timedelta(hours=2)
        observar_documento(d, self.direccion, 'Completar evidencia', hasta=hasta)
        with patch('apps.documentos.models.expediente.timezone.now', return_value=hasta + timedelta(minutes=1)):
            solicitar_entrega_tardia(d, self.coordinador, 'Se necesita obtener una firma adicional')
            habilitar_entrega_tardia(d, self.direccion, hasta=hasta + timedelta(days=1))
            self.assertTrue(d.entrega_abierta)
            self.assertIsNone(d.ultimatum_hasta)

    def test_formulario_y_modal_de_fechas_y_rechazo_post_sin_fecha(self):
        d = self.entrega()
        self.client.force_login(self.direccion)
        url = reverse('admin:reportes-cumplimiento-expediente')
        query = {'anio': ANIO, 'corte': '', 'unidad': self.laboratorio.slug, 'plazos': d.pk}
        self.assertContains(self.client.get(url, query), 'id="plazos-documento"')
        revisar = self.client.get(url, {**query, 'revisar': d.pk})
        self.assertContains(revisar, 'data-rechazo-qr')
        self.assertContains(revisar, 'name="observacion" required')
        self.client.post(url, {'accion': 'observar', 'documento': d.pk, 'observacion': 'Completar'})
        d.refresh_from_db()
        self.assertEqual(d.estado, 'validado')
        hasta = timezone.localtime(timezone.now() + timedelta(days=2)).replace(second=0, microsecond=0)
        self.client.post(url, {'accion': 'observar', 'documento': d.pk,
                              'observacion': 'Completar', 'hasta_correccion': hasta.strftime('%Y-%m-%dT%H:%M')})
        d.refresh_from_db()
        self.assertEqual(d.correccion_hasta, hasta)
        pantalla = self.client.get(reverse('gestion_expediente_unidad', args=[self.laboratorio.slug]),
                                   {'anio': ANIO, 'corte': ''})
        self.assertContains(pantalla, 'Corrección')
        self.assertContains(pantalla, hasta.strftime('%d/%m/%Y %H:%M'))

    def test_correccion_mas_corta_que_ultimatum_no_oculta_su_reapertura(self):
        d = self.entrega()
        d.ultimatum_hasta = timezone.now() + timedelta(days=3)
        d.save(update_fields=['ultimatum_hasta'])
        hasta = timezone.now() + timedelta(hours=2)
        observar_documento(d, self.direccion, 'Completar evidencia', hasta=hasta)
        with patch('apps.documentos.models.expediente.timezone.now', return_value=hasta + timedelta(minutes=1)):
            solicitar_entrega_tardia(d, self.coordinador, 'Falta una firma adicional')
            fila = cumplimiento_de_unidad(self.laboratorio, ANIO)
            casilla = next(c for c in fila['matriz'] if c['documento'].pk == d.pk)
            self.assertTrue(casilla['habilitable'])
            self.assertFalse(casilla['ultimatable'])

    def test_direccion_prioriza_el_enviado_y_separa_la_preparacion(self):
        archivo = self.entrega()
        plan = self.documento(self.laboratorio, 'PLANIFICACION')
        plan.recurso_id, plan.estado, plan.firma_verificada = archivo.recurso_id, 'validado', True
        plan.save()
        def fila_renderizada():
            f = cumplimiento_de_unidad(self.laboratorio, ANIO, self.corte)
            c = next(c for c in f['matriz'] if c['documento'].pk == plan.pk)
            return render_to_string('admin/gestion_unidades/reporteoperativounidad/entrega_compacta.html',
                                    dict(casilla=c, fila=f, user=self.direccion))
        enviado = fila_renderizada()
        self.assertIn('data-acciones-qr', enviado)
        self.assertIn('data-estado-aprobacion="pendiente"', enviado)
        self.assertIn('data-ver-pdf', enviado)
        self.assertNotIn('target="_blank"', enviado)
        self.assertNotIn('borrador=1', enviado)
        self.assertNotIn('Consulta preliminar', enviado)
        plan.estado = 'cargado'
        plan.save(update_fields=['estado'])
        preparado = fila_renderizada()
        self.assertIn('Sin envío', preparado)
        self.assertIn('data-ver-pdf', preparado)
        self.assertNotIn('Consulta preliminar', preparado)
        self.assertEqual(preparado.count('data-ver-pdf'), 1)
        self.assertNotIn('data-pdf-directo', preparado)
        self.assertNotIn('target="_blank"', preparado)
        self.assertNotIn('borrador=1', preparado)

    def test_modal_fuera_del_alcance_no_expone_otras_unidades(self):
        d = self.entrega()
        self.client.force_login(self.direccion)
        pagina = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
            {'anio': ANIO, 'unidad': self.suelto.slug, 'plazos': d.pk})
        self.assertEqual(pagina.status_code, 400)

    def test_catalogo_describe_fecha_fija_y_meses_sin_confundirlos_con_cierre(self):
        panel = admin.site._registry[DocumentoExigido]
        e = DocumentoExigido(plazo_regla='ninguno', fecha_limite=date(2026, 12, 5), hora_limite=time(15, 30))
        self.assertEqual(panel.plazo(e), '05/12/2026 · 15:30')
        e.fecha_limite, e.plazo_regla, e.abre_mes, e.vence_mes = None, 'meses', 5, 8
        self.assertIn('mayo a agosto', panel.plazo(e))
        self.assertNotIn('antes del cierre', panel.plazo(e))
