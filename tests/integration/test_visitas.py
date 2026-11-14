"""Visitas: un papel en una solicitud, no un cuarto tipo de usuario.

Quien organiza la visita tiene cuenta; el grupo, no. La solicitud crea la
reserva de las áreas del recorrido: aforo por área, un guía por cada tantas
personas, protección de visitante del inventario, lista de asistencia en la
puerta y oferta pública en la ficha.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.reservas.presentation.visitas import guias_necesarios, oferta_de_visitas
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import NotificacionReserva
from apps.reservas.models.visitas import SolicitudVisita
from tests.integration.test_laboratorios_institucionales import _dia_habil
from tests.integration.test_produccion_planta import BasePlantaProduce


class BaseVisitas(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organizador = get_user_model().objects.create_user(
            'docente.colegio', 'colegio@ejemplo.ec', 'visita-2026', first_name='Rosa', last_name='Andrade',
        )
        # Quien organiza tiene cuenta y perfil al día: una docente externa.
        perfil = cls.organizador.profile
        perfil.tipo_usuario = 'externo'
        perfil.institucion = 'Unidad Educativa Carchi'
        perfil.save()
        cls.recepcion = EspacioReservable.objects.get(codigo='LAC-AREA-RECEPCION')
        cls.capacitacion = EspacioReservable.objects.get(codigo='LAC-SALA-CAPACITACION')
        cls.queseria = EspacioReservable.objects.get(codigo='LAC-AREA-QUESERIA')
        cls.fecha = _dia_habil(cls.hoy + timedelta(days=6))

    def solicitar(self, usuario=None, **extra):
        datos = {
            'institucion': 'Unidad Educativa Carchi',
            'proposito': 'academica',
            'personas': '12',
            'rango_edades': '15 a 17 años',
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '09:00',
            'hora_fin': '11:00',
            'recorrido': [str(self.capacitacion.pk)],
            'descripcion': 'Conocer la planta y sus procesos.',
            'asistentes': 'Ana Pérez; 0401234567\nLuis Mora',
            'requisitos_aceptados': 'on',
        }
        datos.update(extra)
        self.client.force_login(usuario or self.organizador)
        return self.client.post(reverse('solicitar_visita', args=[self.unidad.slug]), datos)

    def accion(self, reserva, accion, **extra):
        self.client.force_login(self.coordinacion)
        datos = {'accion': accion, 'observacion': f'{accion} desde la prueba.'}
        datos.update(extra)
        return self.client.post(reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]), datos)


class LaOfertaDeVisitasTests(BaseVisitas):
    def test_la_ficha_ofrece_las_visitas_y_el_grupo_no_necesita_cuenta(self):
        oferta = oferta_de_visitas(self.unidad)
        self.assertTrue(oferta['acepta'])
        self.assertEqual(
            [area.codigo for area in oferta['areas']],
            ['LAC-AREA-RECEPCION', 'LAC-LINEA-PROCESO', 'LAC-SALA-CAPACITACION'],
        )
        self.assertEqual(oferta['aforo'], 6)
        self.assertEqual(oferta['personas_por_guia'], 15)
        self.assertEqual(oferta['costo_por_guia'], Decimal('12.00'))
        codigos = [requisito.codigo for requisito in oferta['requisitos']]
        self.assertIn('LAC-ACC-ESCOLTA', codigos)
        self.assertIn('LAC-ACC-COFIA', codigos)
        self.assertNotIn('LAC-ACC-GUANTES', codigos)
        self.assertEqual(guias_necesarios(15, 15), 1)
        self.assertEqual(guias_necesarios(16, 15), 2)
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertNotContains(ficha, 'data-id="visitas-unidad"')
        self.client.force_login(self.coordinacion)
        ficha_interna = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha_interna, 'data-id="visitas-unidad"')
        self.client.logout()
        pagina = self.client.get(reverse('oferta_visitas', args=[self.unidad.slug]))
        self.assertContains(pagina, 'Solicitar una visita')
        self.assertContains(pagina, 'Sala de capacitación y degustación')
        self.assertContains(pagina, 'Sala de quesería')
        self.assertContains(pagina, 'Qué no incluye el recorrido')
        self.assertEqual(pagina['X-Frame-Options'], 'SAMEORIGIN')
        formulario = self.client.get(reverse('solicitar_visita', args=[self.unidad.slug]))
        self.assertEqual(formulario.status_code, 302)
        self.assertIn('?reserva=visita', formulario['Location'])
        # Una cuenta sin perfil al día vuelve al perfil, como al reservar.
        incompleto = get_user_model().objects.create_user('sin.perfil', 'sin.perfil@ejemplo.ec', 'x')
        self.client.force_login(incompleto)
        formulario = self.client.post(reverse('solicitar_visita', args=[self.unidad.slug]), {})
        self.assertEqual(formulario.status_code, 302)
        self.assertIn('completar=1', formulario['Location'])
        self.client.force_login(self.organizador)
        formulario = self.client.get(reverse('solicitar_visita', args=[self.unidad.slug]), follow=True)
        self.assertContains(formulario, 'id="reservaForm"')
        self.assertContains(formulario, 'id="visitaResumenReserva"')
        self.assertContains(formulario, 'Área de recepción de leche')

    def test_la_unidad_define_su_oferta_de_visitas(self):
        respuesta = self.operar(
            modulo='oferta_visitas', acepta_visitas='on', personas_por_guia='10',
            visitas_texto='Recorridos los viernes por la tarde.', areas_visitables=[str(self.capacitacion.pk)],
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        oferta = oferta_de_visitas(self.unidad)
        self.assertEqual([area.pk for area in oferta['areas']], [self.capacitacion.pk])
        self.assertEqual(oferta['personas_por_guia'], 10)
        self.assertEqual(oferta['texto'], 'Recorridos los viernes por la tarde.')
        self.assertEqual(self.solicitar().status_code, 302)
        self.assertEqual(SolicitudVisita.objects.get().guias_necesarios, 2)
        cerrada = self.operar(
            modulo='oferta_visitas', acepta_visitas='', personas_por_guia='10',
            areas_visitables=[str(self.capacitacion.pk)],
        )
        self.assertEqual(cerrada.status_code, 200, cerrada.content)
        self.assertFalse(oferta_de_visitas(self.unidad)['acepta'])
        self.client.logout()
        self.assertEqual(self.client.get(reverse('oferta_visitas', args=[self.unidad.slug])).status_code, 404)
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertNotContains(ficha, 'data-id="visitas-unidad"')


class LaSolicitudDeVisitaTests(BaseVisitas):
    def test_la_solicitud_crea_la_reserva_con_recorrido_guias_y_proteccion(self):
        respuesta = self.solicitar()
        self.assertEqual(respuesta.status_code, 302, respuesta.content)
        visita = SolicitudVisita.objects.get(institucion='Unidad Educativa Carchi')
        reserva = visita.reserva
        self.assertIn(reverse('comprobante_reserva', args=[reserva.pk]), respuesta['Location'])
        self.assertEqual(reserva.estado, 'pendiente')
        self.assertEqual(reserva.usuario, self.organizador)
        self.assertEqual(reserva.numero_participantes, 12)
        self.assertEqual(reserva.proposito_codigo, 'vinculacion')
        self.assertEqual(reserva.institucion, 'Unidad Educativa Carchi')
        self.assertEqual(reserva.titulo_solicitud, 'Visita de Unidad Educativa Carchi')
        self.assertEqual(list(reserva.espacios_solicitados.values_list('codigo', flat=True)), ['LAC-SALA-CAPACITACION'])
        self.assertEqual(visita.guias_necesarios, 1)
        self.assertEqual(visita.costo_estimado, Decimal('0.60'))
        self.assertEqual(reserva.costo_estimado, Decimal('0.60'))
        self.assertEqual(reserva.desglose_cotizacion['total_insumos'], '0.60')
        guia = next(item for item in reserva.desglose_cotizacion['componentes_apoyo']
                    if item['categoria'] == 'acompanamiento')
        self.assertEqual(guia['aporte_institucional'], '12.00')
        self.assertEqual(guia['valor_usuario'], '0.00')
        self.assertEqual(visita.rango_edades, '15 a 17 años')
        self.assertTrue(visita.requisitos_aceptados)
        proteccion = {
            pedido.consumible.codigo: pedido.cantidad_solicitada
            for pedido in reserva.consumibles_solicitados.select_related('consumible')
        }
        self.assertEqual(proteccion, {'LAC-PRO-COFIA': Decimal('12.000')})
        self.assertEqual(
            [(asistente.nombre, asistente.documento) for asistente in visita.asistentes.all()],
            [('Ana Pérez', '0401234567'), ('Luis Mora', '')],
        )
        self.assertTrue(NotificacionReserva.objects.filter(reserva=reserva, usuario=self.organizador).exists())
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
        self.assertContains(comprobante, 'Visita de Unidad Educativa Carchi')
        self.assertContains(comprobante, 'Ana Pérez')
        self.assertContains(comprobante, '1 guía')
        # Dos guías los asume la UPEC; dieciséis cofias cuestan $0.80.
        segunda = self.solicitar(
            institucion='Colegio Bolívar', personas='16', fecha=_dia_habil(self.fecha + timedelta(days=1)).isoformat(),
        )
        self.assertEqual(segunda.status_code, 302, segunda.content)
        bolivar = SolicitudVisita.objects.get(institucion='Colegio Bolívar')
        self.assertEqual(bolivar.guias_necesarios, 2)
        self.assertEqual(bolivar.costo_estimado, Decimal('0.80'))

    def test_el_aforo_la_agenda_y_el_recorrido_mandan(self):
        # La recepción admite seis personas: un grupo de doce no cabe.
        respuesta = self.solicitar(recorrido=[str(self.recepcion.pk), str(self.capacitacion.pk)])
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'admite 6 personas')
        self.assertFalse(SolicitudVisita.objects.exists())
        # Un área que no es visitable no entra al recorrido.
        respuesta = self.solicitar(recorrido=[str(self.queseria.pk)])
        self.assertContains(respuesta, 'no están habilitadas para visitas')
        # Sin aceptar los requisitos no hay solicitud; sin anticipación tampoco.
        self.assertContains(self.solicitar(requisitos_aceptados=''), 'Acepta los requisitos')
        self.assertContains(self.solicitar(fecha=self.hoy.isoformat()), 'anticipación')
        self.assertContains(self.solicitar(asistentes='\n'.join(f'Persona {n}' for n in range(13))), 'más nombres')
        self.assertFalse(SolicitudVisita.objects.exists())
        # La agenda: la sala ya está tomada a esa hora por una visita aprobada.
        primera = self.solicitar()
        self.assertEqual(primera.status_code, 302, primera.content)
        reserva = SolicitudVisita.objects.get().reserva
        self.assertEqual(self.accion(reserva, 'aprobar').status_code, 200)
        otra = self.solicitar(usuario=self.docente, institucion='Colegio Bolívar')
        self.assertEqual(otra.status_code, 200)
        self.assertFalse(otra.json()['success'])
        self.assertIn('capacidad', otra.json()['error'])
        self.assertEqual(SolicitudVisita.objects.count(), 1)

    def test_el_panel_asigna_guia_toma_la_asistencia_y_la_visita_inicia(self):
        self.assertEqual(self.solicitar().status_code, 302)
        visita = SolicitudVisita.objects.get()
        reserva = visita.reserva
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=visitas')
        self.assertContains(panel, 'Visitas solicitadas')
        self.assertContains(panel, 'Unidad Educativa Carchi')
        asignado = self.operar(
            modulo='visita', registro_id=str(visita.pk), guia=self.laboratorista.username,
            observaciones='Entrada por el pasillo norte.',
        )
        self.assertEqual(asignado.status_code, 200, asignado.content)
        visita.refresh_from_db()
        self.assertEqual(visita.guia, self.laboratorista)
        self.assertEqual(visita.observaciones, 'Entrada por el pasillo norte.')
        # La sala admite veinte: la visita se aprueba; sin asistencia registrada no inicia.
        self.assertEqual(self.accion(reserva, 'aprobar').status_code, 200)
        self.assertEqual(self.accion(reserva, 'iniciar').status_code, 409)
        url = reverse('asistencia_visita', args=[self.unidad.slug, visita.pk])
        self.client.force_login(self.laboratorista)
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Ana Pérez')
        self.assertContains(pagina, 'Lista de asistencia')
        ana = visita.asistentes.get(nombre='Ana Pérez')
        guardado = self.client.post(url, {
            'presentes': [str(ana.pk)], 'nuevos': 'Carla Ruiz; 0402345678', 'observaciones': 'Llegaron dos de doce.',
        })
        self.assertEqual(guardado.status_code, 302)
        self.assertEqual(
            [(asistente.nombre, asistente.asistio) for asistente in visita.asistentes.all()],
            [('Ana Pérez', True), ('Luis Mora', False), ('Carla Ruiz', True)],
        )
        self.assertIsNotNone(visita.asistentes.get(nombre='Ana Pérez').ingreso_en)
        visita.refresh_from_db()
        self.assertEqual(visita.observaciones, 'Llegaron dos de doce.')
        self.assertEqual(self.accion(reserva, 'iniciar').status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'en_proceso')
        # El organizador no toma la asistencia; la unidad sí la ve en la pestaña.
        self.client.force_login(self.organizador)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=visitas')
        self.assertContains(panel, '2 de 3')
