"""Visitas externas sin cuenta e internas vinculadas a identidad institucional."""

import json

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client
from django.urls import reverse

from apps.reservas.models.visitas import SolicitudVisita
from tests.integration.test_visitas import BaseVisitas


class AccesoVisitasTests(BaseVisitas):
    def datos(self, **extra):
        return {
            'unidad_id': self.unidad.pk, 'tipo_solicitud': 'visita', 'aceptar_terminos': 'on',
            'fecha_inicio': f'{self.fecha}T09:00', 'fecha_fin': f'{self.fecha}T11:00',
            'horas_seleccionadas': '[9,10]', 'visita_institucion': 'Colegio externo QA',
            'visita_categoria': 'externa', 'visita_conteo': 'lista', 'visita_personas': '1',
            'visita_proposito': 'academica', 'visita_recorrido': [str(self.capacitacion.pk)],
            'visita_requisitos_aceptados': 'on', 'visita_responsable_nombre': 'Persona externa QA',
            'visita_responsable_correo': 'responsable@example.org', 'visita_responsable_telefono': '0990000000',
            'visita_asistentes_json': json.dumps([{'nombre': 'Visitante QA', 'rol': 'otro'}]),
            **extra,
        }

    def test_externa_sin_sesion_conserva_contacto_y_ocupa_agenda_sin_crear_cuentas(self):
        cuentas = get_user_model().objects.count()
        datos = self.datos(visita_conteo='estimado', visita_personas='12')
        result = self.client.post(reverse('crear_reserva'), datos)
        self.assertEqual(result.status_code, 200, result.content)
        visita = SolicitudVisita.objects.get(pk=result.json()['visita_id'])
        self.assertIsNone(visita.responsable_id)
        self.assertIsNone(visita.reserva.usuario_id)
        self.assertEqual(visita.categoria, 'externa')
        self.assertEqual(visita.reserva.nombre_solicitante, 'Persona externa QA')
        self.assertEqual(visita.reserva.correo_solicitante, 'responsable@example.org')
        self.assertEqual(visita.reserva.telefono_solicitante, '0990000000')
        self.assertEqual(get_user_model().objects.count(), cuentas)
        self.assertEqual(result.json()['comprobante_url'], '')
        self.assertTrue(result.json()['numero_referencia'])
        second = self.client.post(reverse('crear_reserva'), datos)
        self.assertEqual(second.status_code, 400, second.content)
        self.assertEqual(SolicitudVisita.objects.count(), 1)

    def test_interna_recursos_servicios_y_busqueda_no_admiten_anonimos(self):
        self.assertEqual(self.client.post(reverse('crear_reserva'), self.datos(visita_categoria='interna')).status_code, 403)
        for tipo in ('recursos', 'servicio'):
            self.assertEqual(self.client.post(reverse('crear_reserva'), self.datos(tipo_solicitud=tipo)).status_code, 401)
        self.assertEqual(self.client.get(reverse('buscar_usuarios_reserva'), {'q': 'Ana', 'contexto': 'visitas_internas'}).status_code, 401)
        self.assertFalse(SolicitudVisita.objects.exists())

    def test_externa_valida_contacto_y_no_suplanta_un_correo_interno(self):
        for fields in ({'visita_responsable_nombre': ''}, {'visita_responsable_correo': 'sin-arroba'},
                       {'visita_responsable_telefono': ''}, {'visita_responsable_correo': self.coordinacion.email}):
            result = self.client.post(reverse('crear_reserva'), self.datos(**fields))
            self.assertIn(result.status_code, (400, 403), result.content)
        self.assertFalse(SolicitudVisita.objects.exists())

    def test_interna_resuelve_cuentas_en_servidor_y_recalcula_el_conteo(self):
        self.client.force_login(self.coordinacion)
        result = self.client.post(reverse('crear_reserva'), self.datos(
            visita_categoria='interna', visita_personas='199', visita_conteo='estimado',
            visita_usuarios_json=json.dumps([self.laboratorista.pk]),
            visita_asistentes_json=json.dumps([{'nombre': 'Nombre falsificado', 'rol': 'otro'}]),
        ))
        self.assertEqual(result.status_code, 200, result.content)
        visita = SolicitudVisita.objects.get(pk=result.json()['visita_id'])
        self.assertEqual(visita.categoria, 'interna')
        self.assertEqual(visita.personas, 1)
        asistente = visita.asistentes.get()
        self.assertEqual(asistente.usuario_id, self.laboratorista.pk)
        self.assertEqual(asistente.nombre, self.laboratorista.get_full_name())
        self.assertEqual(asistente.correo, self.laboratorista.email)
        self.assertEqual(asistente.documento, self.laboratorista.profile.cedula or '')

    def test_interna_rechaza_duplicados_externos_inexistentes_y_lista_vacia(self):
        self.client.force_login(self.coordinacion)
        for ids in ([self.laboratorista.pk, self.laboratorista.pk], [self.organizador.pk], [99999999], []):
            result = self.client.post(reverse('crear_reserva'), self.datos(visita_categoria='interna', visita_usuarios_json=json.dumps(ids)))
            self.assertEqual(result.status_code, 400, result.content)
        self.assertFalse(SolicitudVisita.objects.exists())

    def test_busqueda_interna_incluye_perfil_y_excluye_cuentas_externas(self):
        self.client.force_login(self.coordinacion)
        for usuario, incluido in ((self.laboratorista, True), (self.organizador, False)):
            result = self.client.get(reverse('buscar_usuarios_reserva'), {'q': usuario.username, 'contexto': 'visitas_internas'})
            self.assertEqual(result.status_code, 200, result.content)
            self.assertEqual(bool(result.json()['usuarios']), incluido)

    def test_envio_publico_conserva_csrf(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse('crear_reserva')
        self.assertEqual(client.post(url, self.datos()).status_code, 403)
        client.get(self.unidad.get_absolute_url())
        result = client.post(url, self.datos(), HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
        self.assertEqual(result.status_code, 200, result.content)

    def test_unidad_puede_revisar_y_aprobar_la_solicitud_sin_cuenta(self):
        result = self.client.post(reverse('crear_reserva'), self.datos())
        self.assertEqual(result.status_code, 200, result.content)
        visita = SolicitudVisita.objects.get(pk=result.json()['visita_id'])
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=visitas')
        self.assertContains(panel, 'responsable@example.org')
        self.assertContains(panel, '0990000000')
        comprobante = self.client.get(reverse('comprobante_reserva', args=[visita.reserva_id]))
        self.assertEqual(comprobante.status_code, 200, comprobante.content)
        self.assertEqual(self.accion(visita.reserva, 'aprobar').status_code, 200)
