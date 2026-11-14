"""Expedientes extensos conservan alcance privado y páginas independientes."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.identidades import identidad_de
from apps.centros_id.models import (
    CentroID, Integrante, RegistroSolicitud, SesionAcompanamiento, SolicitudCentro, TareaSolicitud,
)


class PaginacionExpedientesTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}
    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroID.objects.create(nombre='Atención', slug='centro-paginas-privadas', proposito='Investigar')
        cls.usuario = get_user_model().objects.create_user('titular.paginas')
        cls.ajeno = get_user_model().objects.create_user('ajeno.paginas')
        cuenta, otra = identidad_de(cls.usuario), identidad_de(cls.ajeno)
        SolicitudCentro.objects.bulk_create([SolicitudCentro(centro=cls.centro, usuario=cuenta, tipo='reto',
            titulo=f'Solicitud propia {i:03}', problema='Necesidad propia', resultado_esperado='Validación') for i in range(63)])
        cls.solicitud = cls.centro.solicitudes.order_by('pk').first()
        SolicitudCentro.objects.create(centro=cls.centro, usuario=otra, tipo='reto', titulo='EXPEDIENTE_AJENO',
            problema='INFORMACION_AJENA', resultado_esperado='Validación')
        RegistroSolicitud.objects.bulk_create([RegistroSolicitud(solicitud=cls.solicitud,
            estado_nuevo='recibida', detalle=f'Seguimiento {i:03}') for i in range(93)])
        persona = Integrante.objects.create(centro=cls.centro, nombre='Responsable', rol='tecnico')
        inicio = timezone.now() + timedelta(days=1)
        SesionAcompanamiento.objects.bulk_create([SesionAcompanamiento(solicitud=cls.solicitud, responsable=persona,
            inicio=inicio + timedelta(days=i), fin=inicio + timedelta(days=i, hours=1), modalidad='Presencial') for i in range(30)])
        TareaSolicitud.objects.bulk_create([TareaSolicitud(solicitud=cls.solicitud, titulo=f'Compromiso {i:03}',
            a_cargo='centro', plazo=timezone.localdate() + timedelta(days=i)) for i in range(30)])

    def test_solicitudes_propias_paginadas_sin_nombres_ajenos(self):
        self.client.force_login(self.usuario)
        url = reverse('solicitar_centro_id', args=[self.centro.slug])
        paginas = [self.client.get(url, {'tipo': 'reto', 'pagina_solicitudes': numero}) for numero in (1, 2, 3)]
        ids = [[s.pk for s in p.context['mis_solicitudes']] for p in paginas]
        self.assertEqual([len(p) for p in ids], [25, 25, 13])
        self.assertEqual(len(set(sum(ids, []))), 63)
        for respuesta in paginas:
            self.assertEqual(respuesta.status_code, 200)
            self.assertNotContains(respuesta, 'EXPEDIENTE_AJENO')
            self.assertNotContains(respuesta, 'INFORMACION_AJENA')
        self.assertIn('tipo=reto', paginas[1].context['paginacion_solicitudes']['siguiente_url'])
        self.assertTrue(paginas[1].context['paginacion_solicitudes']['siguiente_url'].endswith('#mis-solicitudes'))

    def test_historial_sesiones_y_tareas_paginan_independientemente_sin_perder_registros(self):
        self.client.force_login(self.usuario)
        url = reverse('solicitud_detalle_centro_id', args=[self.centro.slug, self.solicitud.pk])
        respuestas = [self.client.get(url, {'pagina_historial': n, 'pagina_sesiones': 2, 'pagina_tareas': 2})
                      for n in (1, 2, 3)]
        ids = [[evento.pk for evento in r.context['historial']] for r in respuestas]
        self.assertEqual([len(p) for p in ids], [40, 40, 13])
        self.assertEqual(len(set(sum(ids, []))), 93)
        respuesta = respuestas[1]
        self.assertEqual(len(respuesta.context['sesiones']), 5)
        self.assertEqual(len(respuesta.context['tareas']), 5)
        self.assertContains(respuesta, 'Página 2 de 3')
        enlace = respuesta.context['paginacion_historial']['siguiente_url']
        self.assertIn('pagina_sesiones=2', enlace)
        self.assertIn('pagina_tareas=2', enlace)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(url, {'pagina_historial': 2}).status_code, 404)
