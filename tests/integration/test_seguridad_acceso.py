"""Seguridad industrial y acceso: lo que la planta exige y quién lo cumple.

La planta declara sus requisitos por categoría de persona; la solicitud
avisa lo pendiente; la aprobación respeta el aforo; la sesión no empieza
sin el registro de ingreso; solo entra quien cumple; una inducción cerrada
habilita a quienes asistieron; y la práctica por proceso suma la
protección que la planta entrega por persona.
"""

import json
import re
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.reservas.presentation.proceso import seleccion_por_proceso
from apps.reservas.presentation.seguridad import acceso_de_reserva, categoria_de_usuario, estado_de_persona, otorgar_habilitaciones_por_sesion
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso
from apps.reservas.models.reservas import Reserva
from tests.integration.test_laboratorios_institucionales import _dia_habil
from tests.integration.test_produccion_planta import BasePlantaProduce
from tests.integration.utiles import identificar


class BaseAccesoPlanta(BasePlantaProduce):
    """La planta con su reglamento de ingreso cargado y dos estudiantes."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Usuario = get_user_model()
        cls.estudiantes = []
        for numero in (1, 2):
            estudiante = Usuario.objects.create_user(
                username=f'estudiante{numero}.lacteos',
                password='Clave-Estudiante-2026',
                email=f'estudiante{numero}.lacteos@upec.edu.ec',
            )
            identificar(estudiante, tipo_usuario='estudiante')
            cls.estudiantes.append(estudiante)
        cls.recepcion = EspacioReservable.objects.get(codigo='LAC-AREA-RECEPCION')

    def requisito(self, codigo):
        return RequisitoAcceso.objects.get(unidad=self.unidad, codigo=codigo)

    def habilitar(self, usuario, codigo, fecha=None):
        return HabilitacionAcceso.objects.create(
            usuario=usuario,
            requisito=self.requisito(codigo),
            fecha=fecha or self.hoy,
            origen='manual',
            otorgada_por=self.coordinacion,
        )

    def solicitud(self, **extra):
        """Una sesión de investigación en la recepción con el tanque y dos estudiantes."""
        fecha = extra.pop('fecha', self.inicio).isoformat()
        datos = self._payload(
            fecha_inicio=f'{fecha}T09:00',
            fecha_fin=f'{fecha}T11:00',
            incluye_espacio='1',
            alcance_espacio='areas',
            espacios_solicitados=[str(self.recepcion.pk)],
            unidades_seleccionadas=self._seleccion('LAC-EQP-TANQ-01'),
            participantes_seleccionados=json.dumps([estudiante.pk for estudiante in self.estudiantes]),
        )
        datos.update(extra)
        return datos

    def reservar(self, usuario=None, **extra):
        self.client.force_login(usuario or self.docente)
        return self.client.post(reverse('crear_reserva'), self.solicitud(**extra))

    def accion(self, reserva, accion, usuario=None, **extra):
        self.client.force_login(usuario or self.coordinacion)
        datos = {'accion': accion, 'observacion': f'{accion} desde la prueba.'}
        datos.update(extra)
        return self.client.post(reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]), datos)

    def participante(self, reserva, usuario):
        return reserva.registros_participantes.get(usuario=usuario)


class ElReglamentoDeLaPlantaTests(BaseAccesoPlanta):
    def test_la_planta_declara_lo_que_exige_por_categoria_de_persona(self):
        requisitos = list(RequisitoAcceso.objects.filter(unidad=self.unidad, activo=True).order_by('orden'))
        self.assertEqual(len(requisitos), 8)
        induccion = self.requisito('LAC-ACC-INDUCCION')
        self.assertEqual(induccion.tipo, 'induccion')
        self.assertEqual(induccion.vigencia_dias, 180)
        self.assertTrue(induccion.aplica('visitante'))
        salud = self.requisito('LAC-ACC-SALUD')
        self.assertTrue(salud.aplica('estudiante'))
        self.assertFalse(salud.aplica('visitante'))
        cofia = self.requisito('LAC-ACC-COFIA')
        self.assertEqual(cofia.consumible.codigo, 'LAC-PRO-COFIA')
        self.assertEqual(self.requisito('LAC-ACC-RESTRICCIONES').tipo, 'restriccion')
        # Cada quien entra en su categoría: el personal de la planta, los docentes, los estudiantes.
        self.assertEqual(categoria_de_usuario(self.coordinacion, self.unidad), 'personal')
        self.assertEqual(categoria_de_usuario(self.docente, self.unidad), 'docente')
        self.assertEqual(categoria_de_usuario(self.estudiantes[0], self.unidad), 'estudiante')
        estado = {fila['codigo']: fila for fila in estado_de_persona(self.unidad, self.docente, 'docente')}
        self.assertEqual(estado['LAC-ACC-INDUCCION']['estado'], 'pendiente')
        self.assertEqual(estado['LAC-ACC-SALUD']['estado'], 'pendiente')
        self.assertEqual(estado['LAC-ACC-COFIA']['estado'], 'ingreso')
        self.habilitar(self.docente, 'LAC-ACC-INDUCCION')
        estado = {fila['codigo']: fila for fila in estado_de_persona(self.unidad, self.docente, 'docente')}
        self.assertEqual(estado['LAC-ACC-INDUCCION']['estado'], 'vigente')
        self.assertEqual(estado['LAC-ACC-INDUCCION']['vence'], (self.hoy + timedelta(days=180)).isoformat())
        # Una habilitación vencida no cuenta.
        HabilitacionAcceso.objects.all().delete()
        self.habilitar(self.docente, 'LAC-ACC-INDUCCION', fecha=self.hoy - timedelta(days=200))
        estado = {fila['codigo']: fila for fila in estado_de_persona(self.unidad, self.docente, 'docente')}
        self.assertEqual(estado['LAC-ACC-INDUCCION']['estado'], 'pendiente')

    def test_la_practica_por_proceso_suma_la_proteccion_por_persona(self):
        seleccion = seleccion_por_proceso(self.receta_queso, Decimal('2'), personas=16)
        insumos = {insumo['nombre']: insumo for insumo in seleccion['insumos']}
        self.assertEqual(insumos['Cofia desechable']['cantidad'], '16')
        self.assertEqual(insumos['Guantes de nitrilo']['cantidad'], '32')
        self.assertEqual(insumos['Cofia desechable']['clasificacion'], 'Protección por persona')
        self.assertEqual(seleccion['personas'], 16)
        self.client.force_login(self.docente)
        url = reverse('seleccion_por_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        datos = self.client.get(url + '?factor=1&personas=5').json()
        cofia = next(insumo for insumo in datos['insumos'] if insumo['nombre'] == 'Cofia desechable')
        self.assertEqual(cofia['cantidad'], '5')

    def test_la_ficha_y_el_asistente_muestran_lo_que_se_exige(self):
        self.client.force_login(self.docente)
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'Para ingresar a la unidad')
        self.assertContains(ficha, 'Certificado de salud o carné de manipulador de alimentos')
        acceso = json.loads(re.search(r'<script id="accesoReserva" type="application/json">(.*?)</script>', ficha.content.decode(), re.S).group(1))
        self.assertEqual(acceso['categoria'], 'docente')
        induccion = next(fila for fila in acceso['requisitos'] if fila['codigo'] == 'LAC-ACC-INDUCCION')
        self.assertEqual(induccion['estado'], 'pendiente')
        self.assertEqual(induccion['detalle'], 'Sin inducción vigente: la unidad la programa')


class ElPanelDeSeguridadTests(BaseAccesoPlanta):
    def test_la_planta_declara_un_requisito_y_habilita_a_una_persona(self):
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'seguridad'})
        self.assertContains(panel, 'data-management-target="seguridad"')
        self.assertContains(panel, 'LAC-ACC-INDUCCION')
        self.assertContains(panel, 'data-agenda-operation-form="ingreso"')
        respuesta = self.operar(
            modulo='requisito_acceso', codigo='lac-acc-gafas', nombre='Gafas de seguridad en la limpieza',
            tipo='proteccion', aplica_a=['estudiante', 'docente'], obligatorio='1', momento='ingresar',
            descripcion='Para el lavado con detergente alcalino.', orden='9',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        gafas = self.requisito('LAC-ACC-GAFAS')
        self.assertEqual(gafas.aplica_a, ['estudiante', 'docente'])
        self.assertEqual(RequisitoAcceso.objects.filter(unidad=self.unidad, activo=True).count(), 9)
        editada = self.operar(
            modulo='requisito_acceso', registro_id=gafas.pk, codigo='LAC-ACC-GAFAS', nombre='Gafas de seguridad',
            tipo='proteccion', aplica_a=['estudiante'], momento='ingresar',
        )
        self.assertEqual(editada.status_code, 200, editada.content)
        gafas.refresh_from_db()
        self.assertEqual(gafas.nombre, 'Gafas de seguridad')
        self.assertFalse(gafas.obligatorio)
        # La protección no se habilita por persona; la inducción sí, con la vigencia del requisito.
        rechazo = self.operar(
            self.laboratorista, modulo='habilitacion_acceso', persona=self.docente.username,
            requisito_id=self.requisito('LAC-ACC-COFIA').pk,
        )
        self.assertEqual(rechazo.status_code, 400)
        desconocida = self.operar(
            self.laboratorista, modulo='habilitacion_acceso', persona='nadie.conocido',
            requisito_id=self.requisito('LAC-ACC-INDUCCION').pk,
        )
        self.assertEqual(desconocida.status_code, 400)
        self.assertIn('No encontramos', desconocida.json()['error'])
        otorgada = self.operar(
            self.laboratorista, modulo='habilitacion_acceso', persona=self.docente.email,
            requisito_id=self.requisito('LAC-ACC-INDUCCION').pk, fecha=self.hoy.isoformat(), origen='manual',
            observaciones='Inducción dictada en la planta.',
        )
        self.assertEqual(otorgada.status_code, 200, otorgada.content)
        habilitacion = HabilitacionAcceso.objects.get(usuario=self.docente)
        self.assertEqual(habilitacion.vence, self.hoy + timedelta(days=180))
        self.assertEqual(habilitacion.otorgada_por, self.laboratorista)
        # Un estudiante no opera la seguridad de la planta.
        ajeno = self.operar(
            self.estudiantes[0], modulo='habilitacion_acceso', persona=self.docente.username,
            requisito_id=self.requisito('LAC-ACC-SALUD').pk,
        )
        self.assertEqual(ajeno.status_code, 403)


class LaSesionConControlDeIngresoTests(BaseAccesoPlanta):
    def test_la_solicitud_avisa_lo_pendiente_y_el_comprobante_lo_muestra(self):
        respuesta = self.reservar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        datos = respuesta.json()
        self.assertEqual(
            datos['acceso_pendiente'],
            ['Inducción de seguridad e inocuidad', 'Certificado de salud o carné de manipulador de alimentos'],
        )
        reserva = Reserva.objects.get(pk=datos['reserva_id'])
        acceso = acceso_de_reserva(reserva)
        self.assertTrue(acceso['controlado'])
        self.assertEqual(len(acceso['personas']), 3)
        self.assertEqual(acceso['pendientes'], 3)
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
        self.assertContains(comprobante, 'Acceso a la unidad')
        self.assertContains(comprobante, 'Pendiente: Inducción de seguridad e inocuidad')

    def test_el_aforo_se_respeta_al_aprobar(self):
        reserva = Reserva.objects.get(pk=self.reservar().json()['reserva_id'])
        self.assertEqual(reserva.numero_participantes, 3)
        EspacioReservable.objects.filter(pk=self.recepcion.pk).update(capacidad=2)
        rechazo = self.accion(reserva, 'aprobar')
        self.assertEqual(rechazo.status_code, 409, rechazo.content)
        self.assertIn('aforo', rechazo.json()['error'].lower())
        EspacioReservable.objects.filter(pk=self.recepcion.pk).update(capacidad=6)
        self.assertEqual(self.accion(reserva, 'aprobar').status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'confirmada')

    def test_solo_entra_quien_cumple_y_la_sesion_empieza_con_el_ingreso(self):
        reserva = Reserva.objects.get(pk=self.reservar().json()['reserva_id'])
        self.assertEqual(self.accion(reserva, 'aprobar').status_code, 200)
        bloqueado = self.accion(reserva, 'iniciar')
        self.assertEqual(bloqueado.status_code, 409, bloqueado.content)
        self.assertIn('Registra el ingreso', bloqueado.json()['error'])
        docente = self.participante(reserva, self.docente)
        primero = self.participante(reserva, self.estudiantes[0])
        segundo = self.participante(reserva, self.estudiantes[1])
        ids = f'{docente.pk},{primero.pk},{segundo.pk}'
        # Sin inducción ni certificado, la docente no puede marcarse como «ingresa».
        rechazo = self.operar(
            self.laboratorista, modulo='ingreso', reserva_id=reserva.pk, personas_ids=ids,
            **{
                f'persona_{docente.pk}_ingresa': '1', f'persona_{docente.pk}_proteccion': '1',
                f'persona_{docente.pk}_restricciones': '1',
                f'persona_{primero.pk}_motivo': 'Sin inducción', f'persona_{segundo.pk}_motivo': 'Sin inducción',
            },
        )
        self.assertEqual(rechazo.status_code, 400, rechazo.content)
        self.assertIn('Inducción de seguridad e inocuidad', rechazo.json()['error'])
        self.assertEqual(RegistroIngreso.objects.count(), 0)
        self.habilitar(self.docente, 'LAC-ACC-INDUCCION')
        self.habilitar(self.docente, 'LAC-ACC-SALUD')
        # Con la protección sin verificar tampoco entra.
        sin_cofia = self.operar(
            self.laboratorista, modulo='ingreso', reserva_id=reserva.pk, personas_ids=ids,
            **{
                f'persona_{docente.pk}_ingresa': '1', f'persona_{docente.pk}_restricciones': '1',
                f'persona_{primero.pk}_motivo': 'Sin inducción', f'persona_{segundo.pk}_motivo': 'Sin inducción',
            },
        )
        self.assertEqual(sin_cofia.status_code, 400)
        self.assertIn('protección personal verificada', sin_cofia.json()['error'])
        registrado = self.operar(
            self.laboratorista, modulo='ingreso', reserva_id=reserva.pk, personas_ids=ids,
            **{
                f'persona_{docente.pk}_ingresa': '1', f'persona_{docente.pk}_proteccion': '1',
                f'persona_{docente.pk}_restricciones': '1', f'persona_{docente.pk}_hora': '09:05',
                f'persona_{primero.pk}_motivo': 'Sin inducción vigente',
                f'persona_{segundo.pk}_motivo': 'Sin inducción vigente',
            },
        )
        self.assertEqual(registrado.status_code, 200, registrado.content)
        self.assertEqual(RegistroIngreso.objects.filter(reserva=reserva).count(), 3)
        ingreso = RegistroIngreso.objects.get(reserva=reserva, participante=docente)
        self.assertTrue(ingreso.ingresa)
        self.assertEqual(ingreso.hora_ingreso.strftime('%H:%M'), '09:05')
        self.assertTrue(ingreso.habilitaciones_vigentes)
        negado = RegistroIngreso.objects.get(reserva=reserva, participante=primero)
        self.assertFalse(negado.ingresa)
        self.assertIn('Inducción de seguridad e inocuidad', negado.pendientes)
        acceso = acceso_de_reserva(reserva)
        self.assertEqual(acceso['ingresados'], 1)
        self.assertEqual(acceso['sin_registro'], 0)
        self.assertTrue(acceso['listo'])
        self.assertEqual(self.accion(reserva, 'iniciar').status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'en_proceso')
        expediente = self.client.get(reverse('gestion_reserva_detalle', args=[self.unidad.slug, reserva.pk])).json()
        self.assertEqual(expediente['reserva']['acceso']['ingresados'], 1)
        persona_docente = next(p for p in expediente['reserva']['acceso']['personas'] if p['participante_id'] == docente.pk)
        self.assertTrue(persona_docente['ingreso']['ingresa'])

    def test_un_laboratorio_sin_requisitos_no_cambia(self):
        RequisitoAcceso.objects.filter(unidad=self.unidad).update(activo=False)
        respuesta = self.reservar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()['acceso_pendiente'], [])
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertFalse(acceso_de_reserva(reserva)['controlado'])
        self.assertEqual(self.accion(reserva, 'aprobar').status_code, 200)
        self.assertEqual(self.accion(reserva, 'iniciar').status_code, 200)


class LaInduccionComoSesionTests(BaseAccesoPlanta):
    def test_cerrar_la_induccion_habilita_a_quienes_asistieron(self):
        ayer = _dia_habil(self.hoy - timedelta(days=4))
        respuesta = self.reservar(
            fecha=ayer,
            proposito='Capacitación',
            proposito_codigo='capacitacion',
            subtipo_actividad='induccion',
            referencia_actividad='Inducción de seguridad e inocuidad de la planta',
            descripcion_proyecto='Buenas prácticas de manufactura, riesgos y emergencias.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        # A la inducción se viene sin inducción: no cuenta como pendiente para entrar.
        acceso = acceso_de_reserva(reserva)
        estudiante = next(p for p in acceso['personas'] if p['categoria'] == 'estudiante')
        self.assertNotIn('Inducción de seguridad e inocuidad', estudiante['pendientes'])
        reserva.estado = 'confirmada'
        reserva.save(update_fields=['estado'])
        cierre = self.accion(
            reserva, 'completar', ejecucion_registrada='1',
            participantes_seleccionados=json.dumps([{'id': e.pk, 'asistencia': 'asistio'} for e in self.estudiantes]),
            asistencia_solicitante='asistio', ejecucion_hora_inicio='09:00', ejecucion_hora_fin='11:00',
            ejecucion_asistentes_total='3', ejecucion_cumplimiento='si',
            ejecucion_observaciones='Inducción dictada a todo el grupo.',
        )
        self.assertEqual(cierre.status_code, 200, cierre.content)
        habilitaciones = HabilitacionAcceso.objects.filter(reserva=reserva, origen='sesion')
        self.assertEqual(habilitaciones.count(), 3)
        self.assertEqual({h.usuario for h in habilitaciones}, {self.docente, *self.estudiantes})
        self.assertTrue(all(h.vence == ayer + timedelta(days=180) for h in habilitaciones))
        self.assertTrue(all(h.requisito.codigo == 'LAC-ACC-INDUCCION' for h in habilitaciones))
        self.assertEqual(otorgar_habilitaciones_por_sesion(reserva, self.coordinacion), 0)
        estado = {fila['codigo']: fila for fila in estado_de_persona(self.unidad, self.estudiantes[0], 'estudiante')}
        self.assertEqual(estado['LAC-ACC-INDUCCION']['estado'], 'vigente')
