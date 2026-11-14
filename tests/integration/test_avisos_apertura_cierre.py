"""La apertura prepara el informe provisional sin anticipar el resultado final."""
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.documentos.models.avisos_documentales import AvisoDocumental
from apps.documentos.presentation.avisos_documentales import (
    HORAS_MARCADOR_APERTURA, _datos_aviso_apertura, enviar_pendientes, preparar_avisos,
)
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente


def instante(fecha, hora=time(12)):
    return timezone.make_aware(datetime.combine(fecha, hora))


class AvisoAperturaContenidoTests(SimpleTestCase):
    def documento(self, **cambios):
        plazo = instante(date(2031, 1, 15), time(23, 59))
        valores = dict(marco_periodo='gestion_v1',
            exigido=SimpleNamespace(codigo='INFORME-SEMESTRAL', plazo_regla='cierre',
                                    anexo_de_id=None, activo=True),
            unidad=SimpleNamespace(nombre='FabLab', slug='fablab', activo=True),
            nombre_documental='Informe semestral', estado='pendiente',
            prorroga_hasta=None, correccion_hasta=None, ultimatum_hasta=None,
            abre_el=date(2030, 12, 16), plazo_entrega=plazo, anio=2030, corte='B',
            tramo_inicio=date(2030, 7, 1), tramo_fin=date(2030, 12, 31))
        valores.update(cambios)
        return SimpleNamespace(**valores)

    def test_apertura_pide_preparar_provisional_no_declarar_cierre(self):
        datos = _datos_aviso_apertura(self.documento(), instante(date(2030, 12, 16)))
        self.assertEqual(datos['tipo'], 'apertura')
        self.assertIn('Prepara el informe provisional', datos['mensaje'])
        self.assertIn('El período termina el 31/12/2030', datos['mensaje'])
        self.assertIn('después del fin del período y hasta 15/01/2031', datos['mensaje'])
        self.assertIn('no acredita el cierre', datos['mensaje'])

    def test_antes_de_apertura_y_despues_de_plazo_no_se_prepara(self):
        documento = self.documento()
        self.assertIsNone(_datos_aviso_apertura(documento, instante(date(2030, 12, 15))))
        self.assertIsNone(_datos_aviso_apertura(documento, documento.plazo_entrega + timedelta(seconds=1)))
        self.assertIsNotNone(_datos_aviso_apertura(documento, documento.plazo_entrega))

    def test_despues_del_periodo_pide_informe_final_con_alcance_conservado(self):
        datos = _datos_aviso_apertura(self.documento(), instante(date(2031, 1, 2)))
        self.assertNotIn('informe provisional', datos['mensaje'])
        self.assertIn('Completa el informe final', datos['mensaje'])
        self.assertIn('no amplía las fechas', datos['mensaje'])

    def test_apertura_excluye_legado_enviados_inactivos_y_correcciones(self):
        ahora = instante(date(2030, 12, 16))
        for cambios in (dict(marco_periodo='academico_legacy'), dict(estado='validado'),
                        dict(estado='no_aplica'), dict(correccion_hasta=ahora + timedelta(days=4)),
                        dict(prorroga_hasta=ahora + timedelta(days=4)),
                        dict(ultimatum_hasta=ahora + timedelta(days=4)), dict(abre_el=None)):
            with self.subTest(cambios=cambios):
                self.assertIsNone(_datos_aviso_apertura(self.documento(**cambios), ahora))
        documento = self.documento()
        documento.exigido.anexo_de_id = 1
        self.assertIsNone(_datos_aviso_apertura(documento, ahora))


class AvisoAperturaColaTests(BaseDelExpediente):
    """Preparadas para el runner aislado; nunca se ejecutan contra datos operativos."""
    def cierre(self):
        documento = self.documento(self.laboratorio, 'INFORME-SEMESTRAL', corte='B')
        documento.exigido.plazo_regla = 'cierre'
        documento.exigido.plazo_dias = documento.exigido.apertura_dias = 15
        documento.exigido.hora_limite = time(23, 59)
        documento.exigido.save()
        documento.anio = 2030
        documento.marco_periodo = 'gestion_v1'
        documento.tramo_inicio, documento.tramo_fin = date(2030, 7, 1), date(2030, 12, 31)
        documento.abre_el, documento.vence_el = date(2030, 12, 16), date(2031, 1, 15)
        documento.estado = 'pendiente'
        documento.save()
        return documento

    def test_preparar_deduplica_no_envia_ni_cambia_estado_o_evaluacion(self):
        documento = self.cierre()
        ahora = instante(documento.abre_el)
        with patch('apps.documentos.presentation.avisos_documentales.send_mail') as correo, patch(
                'apps.documentos.presentation.avisos_documentales.import_string') as proveedor:
            preparar_avisos(ahora)
            preparar_avisos(ahora)
        correo.assert_not_called()
        proveedor.assert_not_called()
        avisos = AvisoDocumental.objects.filter(documento=documento)
        self.assertEqual(avisos.count(), 1)
        aviso = avisos.get()
        self.assertEqual((aviso.tipo, aviso.horas, aviso.intentos), ('apertura', HORAS_MARCADOR_APERTURA, 0))
        self.assertFalse(aviso.email_enviado or aviso.sms_enviado)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'pendiente')
        self.assertIsNone(documento.evaluacion)

    def test_apertura_no_ocupa_la_clave_de_evaluacion_y_conserva_7d_y_24h(self):
        from apps.documentos.presentation.incumplimiento_documental import avisar

        documento = self.cierre()
        preparar_avisos(instante(documento.abre_el))
        preparar_avisos(documento.plazo_entrega - timedelta(days=7))
        preparar_avisos(documento.plazo_entrega - timedelta(hours=24))
        avisar(documento, documento.plazo_entrega, 'evaluacion', 'Aviso de evaluación independiente.')
        avisos = AvisoDocumental.objects.filter(documento=documento)
        self.assertEqual(set(avisos.values_list('horas', flat=True)), {0, 24, 168, HORAS_MARCADOR_APERTURA})
        self.assertEqual(avisos.filter(tipo='evaluacion').count(), 1)
        self.assertEqual(avisos.filter(tipo='apertura').count(), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', DOCUMENT_SMS_BACKEND='')
    def test_envio_descarta_apertura_si_ya_se_envio_o_cambio_el_plazo(self):
        documento = self.cierre()
        ahora = instante(documento.abre_el)
        preparar_avisos(ahora)
        documento.estado = 'validado'
        documento.save(update_fields=['estado'])
        with patch('apps.documentos.presentation.avisos_documentales.send_mail') as correo:
            enviar_pendientes(ahora)
        correo.assert_not_called()
        documento.estado = 'pendiente'
        documento.vence_el += timedelta(days=1)
        documento.save(update_fields=['estado', 'vence_el'])
        with patch('apps.documentos.presentation.avisos_documentales.send_mail') as correo:
            enviar_pendientes(ahora)
        correo.assert_not_called()
        self.assertEqual(AvisoDocumental.objects.get(documento=documento).intentos, 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', DOCUMENT_SMS_BACKEND='')
    def test_envio_revalida_ventana_abierta_y_administrador_actual(self):
        documento = self.cierre()
        ahora = instante(documento.abre_el)
        preparar_avisos(ahora)
        documento.abre_el += timedelta(days=1)
        documento.save(update_fields=['abre_el'])
        with patch('apps.documentos.presentation.avisos_documentales.send_mail') as correo:
            enviar_pendientes(ahora)
        correo.assert_not_called()
        documento.abre_el -= timedelta(days=1)
        documento.save(update_fields=['abre_el'])
        self.laboratorio.administrador = self.direccion
        self.laboratorio.save(update_fields=['administrador'])
        with patch('apps.documentos.presentation.avisos_documentales.send_mail') as correo:
            enviar_pendientes(ahora)
        correo.assert_not_called()
