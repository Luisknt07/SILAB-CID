"""Menos pasos repetidos con la misma trazabilidad.

- validar la ejecución de una práctica registra el cierre de su sesión con la función de «Completar»: la sesión cuenta
  como atendida en el anexo 1, con su rastro, y una sesión ya cerrada no se toca;
- una evidencia guardada como borrador se verifica después, con las reglas del alta y su rastro, y desde entonces la
  medición la cuenta;
- la página 403 dice qué permiso falta y a quién pedirlo, sin datos internos; las operaciones JSON siguen en JSON.
"""
import json
from datetime import date, datetime, time, timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.views.defaults import permission_denied

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.medicion_metas import registros_de_gestion
from apps.formacion.models.practicas import EjecucionPractica, RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from tests.integration.test_rutas_de_captura_uso_y_practicas import BasePracticas, _tabla
from tests.integration.utiles import identificar, pdf_legible_prueba


class ValidarPracticaCierraLaSesionTests(BasePracticas):
    def ejecucion_enviada(self):
        tema, guia, reserva, plan = self.practica_planificada()
        self.registrar_ejecucion(plan, 'enviar', 'bitacora', SimpleUploadedFile(
            'bitacora.pdf', pdf_legible_prueba('Bitácora ficticia'), 'application/pdf'), 'Bitácora de la práctica.')
        return reserva, plan

    def validar(self, plan, despues_de_la_sesion=True):
        ruta = reverse('accion_ejecucion_practica', args=[self.lab.slug, plan.pk])
        if not despues_de_la_sesion:
            return self.como(self.admin).post(ruta, {'accion': 'validar'})
        despues = timezone.make_aware(datetime.combine(self.fecha + timedelta(days=1), time(9, 0)))
        with mock.patch('django.utils.timezone.now', return_value=despues):
            return self.como(self.admin).post(ruta, {'accion': 'validar'})

    def cierres_por_validacion(self, plan):
        return RegistroAuditoriaUnidad.objects.filter(
            unidad=self.lab, descripcion__contains=f'Cierre registrado por la validación de la práctica {plan.codigo}')

    def test_validar_registra_el_cierre_con_horas_asistentes_y_la_cuenta_que_valido(self):
        reserva, plan = self.ejecucion_enviada()
        self.assertEqual(self.validar(plan).status_code, 302)
        reserva.refresh_from_db()
        self.assertTrue(reserva.es_efectiva)
        cierre = reserva.detalle_ejecucion
        self.assertEqual((cierre['horario_real'], cierre['asistentes_total'], cierre['registrada_por_id']),
                         ({'inicio': '09:05', 'fin': '10:55'}, 2, self.admin.pk))
        # Quién asistió, persona por persona, tal como lo declaró la ejecución.
        self.assertEqual({p['asistencia_codigo'] for p in cierre['participantes']}, {'asistio'})
        self.assertEqual(cierre['ejecucion_practica_estado'], 'validada')
        # La auditoría dice que el cierre lo registró la validación y con qué cuenta.
        rastro = self.cierres_por_validacion(plan).get()
        self.assertEqual((rastro.usuario, rastro.entidad), (self.admin, reserva._meta.label))
        sesiones = _tabla(self.anexo('REGISTRO-USO'), '1.1')
        for dato in ('atendidas: 1', 'real 09:05–10:55', '2 asistieron 2'):
            self.assertIn(dato, sesiones)
        # Quien validó no es quien registró la ejecución.
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.assertEqual((ejecucion.estado, ejecucion.creado_por, ejecucion.validado_por),
                         ('validada', self.docente, self.admin))

    def test_una_sesion_ya_cerrada_en_reservas_no_se_toca_al_validar(self):
        reserva, plan = self.ejecucion_enviada()
        self.como(self.admin)
        self.assertEqual(self.decidir(reserva, 'iniciar').status_code, 200)
        respuesta = self.cierre(reserva, asistentes=2, ejecucion_observaciones='Cierre ficticio desde reservas.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        reserva.refresh_from_db()
        cierre_original = reserva.detalle_ejecucion
        self.assertEqual(self.validar(plan).status_code, 302)
        reserva.refresh_from_db()
        self.assertEqual(reserva.detalle_ejecucion, cierre_original)
        self.assertFalse(self.cierres_por_validacion(plan).exists())
        self.assertEqual(EjecucionPractica.objects.get(planificacion=plan).estado, 'validada')

    def test_validar_antes_de_que_termine_la_sesion_avisa_y_la_deja_pendiente_de_cierre(self):
        reserva, plan = self.ejecucion_enviada()
        respuesta = self.validar(plan, despues_de_la_sesion=False)
        avisos = [str(m) for m in get_messages(respuesta.wsgi_request)]
        self.assertTrue(any('Regístralo en «Reservas y agenda» con «Completar»' in aviso for aviso in avisos), avisos)
        reserva.refresh_from_db()
        # La validación no se bloquea; la sesión queda visible como pendiente de su registro de cierre.
        self.assertEqual(EjecucionPractica.objects.get(planificacion=plan).estado, 'validada')
        self.assertFalse(reserva.es_efectiva)
        detalle = self.client.get(reverse('gestion_reserva_detalle', args=[self.lab.slug, reserva.pk])).json()
        self.assertTrue(detalle['reserva']['requiere_cierre'])

    def test_sin_permiso_de_practicas_la_validacion_dice_que_permiso_falta_y_quien_lo_concede(self):
        reserva, plan = self.ejecucion_enviada()
        respuesta = self.como(self.docente).post(
            reverse('accion_ejecucion_practica', args=[self.lab.slug, plan.pk]), {'accion': 'validar'})
        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, 'Necesitas el permiso de prácticas de esta unidad', status_code=403)
        self.assertContains(respuesta, 'Configuración de la unidad → Equipo humano', status_code=403)


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class VerificarBorradorDeEvidenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.coordinadora = usuarios.create_user('coordinadora-k1', first_name='Cora', last_name='Coordinadora')
        identificar(cls.coordinadora, tipo_usuario='administrativo', carrera='')
        cls.laboratorista = usuarios.create_user('laboratorista-k1', first_name='Lalo', last_name='Laboratorista')
        identificar(cls.laboratorista, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio ficticio K1', slug='lab-k1', dependencia='laboratorios', descripcion='.',
            fecha_inicio=date(2026, 1, 1), administrador=cls.coordinadora)
        # Puede registrar evidencias (permiso de reportes), pero no comprobarlas: no es coordinación ni técnico.
        ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.laboratorista, nombre='Lalo Laboratorista',
                                         rol='laboratorista', activo=True, permisos_operativos={'reportes': True})

    def setUp(self):
        self.hoy = date(2026, 10, 16)
        reloj = mock.patch('django.utils.timezone.localdate', return_value=self.hoy)
        reloj.start()
        self.addCleanup(reloj.stop)
        self.ruta = (reverse('fuentes_metas_unidad', args=[self.unidad.slug])
                     + '?anio=2026&corte=B&tipo=CAPACITACION')

    def capacitaciones(self):
        return registros_de_gestion(self.unidad, date(2026, 7, 1), date(2026, 12, 31))['gestion_capacitacion']

    def borrador(self, usuario, **cambios):
        self.client.force_login(usuario)
        datos = dict(codigo='CAP-K1', fecha='2026-10-16', titulo='Capacitación ficticia realizada',
                     descripcion='Constancia ficticia de la capacitación.', responsable=self.coordinadora.pk,
                     enlace='https://example.org/capacitacion/cap-k1')
        datos.update(cambios)
        self.assertEqual(self.client.post(self.ruta, datos).status_code, 302)
        evidencia = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, codigo=datos['codigo'])
        self.assertEqual(evidencia.estado, 'borrador')
        return evidencia

    def verificar(self, evidencia, **datos):
        return self.client.post(self.ruta, {'accion': 'verificar', 'evidencia': str(evidencia.pk), **datos})

    def test_verificar_un_borrador_lo_pasa_a_verificada_con_su_rastro_y_la_medicion_lo_cuenta(self):
        evidencia = self.borrador(self.laboratorista)
        self.assertEqual(self.capacitaciones(), 0)
        self.client.force_login(self.coordinadora)
        self.assertContains(self.client.get(self.ruta), 'Verificar evidencia')
        respuesta = self.verificar(evidencia, verificar='on')
        self.assertEqual(respuesta.status_code, 302)
        evidencia.refresh_from_db()
        self.assertEqual((evidencia.estado, evidencia.validado_por, evidencia.creado_por),
                         ('validado', self.coordinadora, self.laboratorista))
        self.assertIsNotNone(evidencia.validado_en)
        rastro = RegistroAuditoriaUnidad.objects.get(entidad=evidencia._meta.label, objeto_id=str(evidencia.pk),
                                                     accion='aprobar')
        self.assertEqual((rastro.usuario, rastro.datos_anteriores, rastro.datos_nuevos['estado']),
                         (self.coordinadora, {'estado': 'borrador'}, 'validado'))
        self.assertEqual(rastro.descripcion, 'Verificación de evidencia: CAP-K1')
        # Cuenta igual que si se hubiera verificado al registrarla.
        self.assertEqual(self.capacitaciones(), 1)
        self.assertNotContains(self.client.get(self.ruta), 'Verificar evidencia')

    def test_verificar_sin_respaldo_lo_pide_y_lo_recibe_en_el_mismo_paso(self):
        evidencia = self.borrador(self.coordinadora, enlace='')
        self.assertContains(self.client.get(self.ruta), 'Respaldo (PDF o imagen)')
        self.assertContains(self.verificar(evidencia, verificar='on'), 'Adjunta un archivo de la unidad o el enlace')
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.estado, 'borrador')
        respuesta = self.verificar(evidencia, verificar='on', enlace='https://example.org/capacitacion/respaldo-k1')
        self.assertEqual(respuesta.status_code, 302)
        evidencia.refresh_from_db()
        self.assertEqual((evidencia.estado, evidencia.enlace),
                         ('validado', 'https://example.org/capacitacion/respaldo-k1'))
        self.assertEqual(self.capacitaciones(), 1)

    def test_verificar_se_niega_a_quien_no_puede_comprobar_y_sin_la_casilla(self):
        evidencia = self.borrador(self.laboratorista)
        self.assertContains(self.verificar(evidencia, verificar='on'),
                            'un responsable técnico o la coordinación activa')
        self.client.force_login(self.coordinadora)
        self.assertContains(self.verificar(evidencia), 'Marca la casilla de comprobación')
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.estado, 'borrador')
        self.assertEqual(self.capacitaciones(), 0)
        self.assertFalse(RegistroAuditoriaUnidad.objects.filter(
            entidad=evidencia._meta.label, objeto_id=str(evidencia.pk), accion='aprobar').exists())

    def test_la_pantalla_de_simulacros_dice_que_el_borrador_se_verifica_despues(self):
        self.client.force_login(self.coordinadora)
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug]) + '?anio=2026&corte=B&tipo=SIMULACRO'
        respuesta = self.client.get(ruta)
        self.assertContains(respuesta, 'Un borrador se puede verificar después desde la lista')
        self.assertNotContains(respuesta, 'se puede completar después')


class PaginaSinPermisoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.persona = usuarios.create_user('persona-sin-permiso-k1')
        identificar(cls.persona)
        cls.unidad = Unidad.objects.create(nombre='Laboratorio ficticio K1 403', slug='lab-k1-403',
                                           dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))

    @override_settings(MEDICION_METAS_HABILITADA=True)
    def test_la_pagina_403_muestra_el_mensaje_y_salidas_sin_datos_internos(self):
        self.client.force_login(self.persona)
        respuesta = self.client.get(reverse('fuentes_metas_unidad', args=[self.unidad.slug]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTemplateUsed(respuesta, '403.html')
        self.assertContains(respuesta, 'No tienes acceso al registro de evidencias de esta unidad.', status_code=403)
        self.assertContains(respuesta, reverse('home'), status_code=403)
        self.assertContains(respuesta, 'Mis reservas', status_code=403)
        for interno in ('Traceback', 'PermissionDenied', 'apps/', 'File "', 'SECRET'):
            self.assertNotContains(respuesta, interno, status_code=403)

    def test_sin_mensaje_explica_a_quien_pedir_el_permiso_y_sin_sesion_no_ofrece_mis_reservas(self):
        peticion = RequestFactory().get('/')
        from django.contrib.auth.models import AnonymousUser
        peticion.user = AnonymousUser()
        respuesta = permission_denied(peticion, PermissionDenied())
        texto = respuesta.content.decode()
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn('pídelo a la coordinación de tu unidad', texto)
        self.assertNotIn('Mis reservas', texto)

    def test_una_operacion_json_del_panel_sigue_respondiendo_json(self):
        self.client.force_login(self.persona)
        respuesta = self.client.get(reverse('buscar_usuarios_reserva'),
                                    {'contexto': 'responsables', 'unidad': self.unidad.slug, 'q': 'ficticio'})
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta['Content-Type'], 'application/json')
        self.assertEqual(json.loads(respuesta.content)['success'], False)
