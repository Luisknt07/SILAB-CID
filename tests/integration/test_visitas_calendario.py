import json
from datetime import timedelta

from django.urls import reverse

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.reservas.models.visitas import SolicitudVisita
from tests.integration.test_visitas import BaseVisitas


class VisitasEnAsistenteUnicoTests(BaseVisitas):
    def calendario(self, **extra):
        datos = {'desde': self.fecha.isoformat(), 'hasta': (self.fecha + timedelta(days=6)).isoformat(),
                 'tipo_solicitud': 'visita', 'visita_personas': '4', 'espacios': str(self.capacitacion.pk)}
        datos.update(extra)
        return self.client.get(reverse('obtener_ocupacion_laboratorio', args=[self.unidad.pk]), datos)

    def enviar(self, **extra):
        self.client.force_login(self.organizador)
        datos = {
            'unidad_id': self.unidad.pk, 'tipo_solicitud': 'visita', 'aceptar_terminos': 'on',
            'fecha_inicio': f'{self.fecha}T09:00', 'fecha_fin': f'{self.fecha}T11:00',
            'horas_seleccionadas': '[9,10]', 'visita_institucion': 'Colegio de la visita',
            'visita_personas': '4', 'visita_proposito': 'academica', 'visita_rango_edades': '15 a 17',
            'visita_descripcion': 'Conocer el trabajo de la unidad.',
            'visita_recorrido': [str(self.capacitacion.pk)], 'visita_requisitos_aceptados': 'on',
            'visita_asistentes': 'Ana; 123\nLuis',
        }
        datos.update(extra)
        return self.client.post(reverse('crear_reserva'), datos)

    def test_enlace_anterior_abre_la_unidad_y_su_modal_sin_pagina_separada(self):
        response = self.client.get(reverse('solicitar_visita', args=[self.unidad.slug]))
        self.assertRedirects(response, f'{self.unidad.get_absolute_url()}?reserva=visita#reservas-servicios', fetch_redirect_response=False)
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'id="visitaDatosReserva"')
        self.assertContains(ficha, 'id="visitaRecorridoReserva"')
        self.assertContains(ficha, 'id="visitaCondicionesReserva"')
        self.assertContains(ficha, 'id="visitaResumenReserva"')
        self.assertContains(ficha, 'id="monthGrid"', count=1)
        self.assertNotContains(ficha, 'data-visit-calendar')

    def test_agenda_es_la_misma_api_y_conserva_ocupacion_y_eventos(self):
        response = self.calendario()
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json()
        self.assertTrue(result['success'])
        self.assertTrue(result['seleccion_recursos_aplicada'])
        self.assertIn('eventos', result)
        self.assertIn('dias', result)

    def test_antes_de_elegir_areas_la_agenda_muestra_ocupacion_general(self):
        self.solicitar()
        self.client.logout()
        response = self.calendario(espacios='')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn(9, response.json()['dias'][self.fecha.isoformat()]['horas_bloqueadas'])

    def test_agenda_rechaza_areas_no_visitables_y_aforo_excedido(self):
        response = self.calendario(espacios=f'{self.capacitacion.pk},{self.queseria.pk}')
        self.assertEqual(response.status_code, 400)
        self.assertIn('no están habilitadas', response.json()['error'])
        response = self.calendario(visita_personas='200')
        self.assertEqual(response.status_code, 400)
        self.assertIn('admite hasta', response.json()['error'])

    def test_confirmacion_del_modal_crea_visita_y_comprobante_con_las_horas_seleccionadas(self):
        response = self.enviar()
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json()
        self.assertTrue(result['success'])
        visita = SolicitudVisita.objects.get(pk=result['visita_id'])
        self.assertEqual(visita.reserva.estado, 'pendiente')
        self.assertEqual(visita.personas, 4)
        self.assertEqual(visita.institucion, 'Colegio de la visita')
        self.assertEqual(visita.reserva.hora_inicio.hour, 9)
        self.assertEqual(visita.reserva.hora_fin.hour, 11)
        self.assertEqual(json.loads(visita.reserva.horas_seleccionadas), [9, 10])
        self.assertEqual(list(visita.recorrido.all()), [self.capacitacion])
        self.assertEqual(visita.asistentes.count(), 2)
        self.assertEqual(result['comprobante_url'], reverse('comprobante_reserva', args=[visita.reserva_id]))

    def test_horas_discontinuas_o_fechas_incoherentes_no_crean_reserva(self):
        for datos in ({'horas_seleccionadas': '[9,11]'}, {'fecha_fin': f'{self.fecha}T12:00'},
                      {'fecha_inicio': f'{self.fecha}T09:30'}):
            response = self.enviar(**datos)
            self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(SolicitudVisita.objects.exists())

    def test_el_envio_revalida_areas_y_condiciones_aunque_el_cliente_las_altere(self):
        for datos in ({'visita_recorrido': [str(self.queseria.pk)]},
                      {'visita_requisitos_aceptados': ''}, {'aceptar_terminos': ''}):
            response = self.enviar(**datos)
            self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(SolicitudVisita.objects.exists())

    def test_visita_sin_areas_publicadas_se_reserva_en_la_misma_agenda(self):
        EspacioReservable.objects.filter(unidad=self.unidad).update(visitable=False)
        self.assertEqual(self.calendario(espacios='').status_code, 200)
        response = self.enviar(visita_recorrido=[])
        self.assertTrue(response.json()['success'], response.content)
        visita = SolicitudVisita.objects.get()
        self.assertEqual(visita.reserva.alcance_espacio, 'unidad_completa')
        self.assertFalse(visita.recorrido.exists())
        self.assertFalse(EspacioReservable.objects.filter(unidad=self.unidad, visitable=True).exists())

    def test_la_visita_registrada_ocupa_el_calendario_compartido_y_bloquea_otra_incompatible(self):
        response = self.enviar(visita_personas='12')
        self.assertTrue(response.json()['success'], response.content)
        self.client.logout()
        calendario = self.calendario(visita_personas='12')
        self.assertEqual(calendario.status_code, 200, calendario.content)
        day = calendario.json()['dias'][self.fecha.isoformat()]
        self.assertIn(9, day['horas_bloqueadas'])
        self.assertNotContains(calendario, self.organizador.email)
        response = self.enviar(visita_personas='12')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(SolicitudVisita.objects.count(), 1)

    def test_unidad_cerrada_rechaza_consulta_y_envio(self):
        ConfiguracionOperativaUnidad.objects.filter(unidad=self.unidad).update(acepta_visitas=False)
        self.assertEqual(self.calendario().status_code, 400)
        self.assertEqual(self.enviar().status_code, 400)

    def test_sin_datos_de_responsable_no_se_envia_la_visita_externa(self):
        response = self.client.post(reverse('crear_reserva'), {'tipo_solicitud': 'visita'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SolicitudVisita.objects.exists())
