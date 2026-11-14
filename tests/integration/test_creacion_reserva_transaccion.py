from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.reservas.presentation.creacion_transaccion import ComandoCreacionReserva, crear_expediente_reserva
from apps.core.usuarios.pertenencia import pertenencia_actual
from apps.reservas.models.reservas import Reserva, RevisionReserva
from apps.directorio_unidades.models.core import Unidad


class CreacionReservaTransaccionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="transaccion.reserva",
            email="transaccion.reserva@upec.edu.ec",
            password="prueba-segura",
            first_name="Ana",
            last_name="Transacción",
        )
        cls.usuario.profile.telefono = "0999999999"
        cls.usuario.profile.tipo_usuario = "estudiante"
        cls.usuario.profile.institucion = "UPEC"
        cls.usuario.profile.save()
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio transaccional",
            descripcion="Prueba directa del expediente.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-transaccional",
        )

    def comando(self):
        contexto = {
            "subtipo_actividad": "investigacion",
            "alcance_beneficiario": "perfil_solicitante",
            "facultad_beneficiaria": "",
            "carrera_beneficiaria": "",
            "entidad_beneficiaria": "UPEC",
            "vinculacion_actividad": "no_aplica",
            "actividad_catalogo": None,
            "referencia_actividad": "",
            "codigo_referencia_actividad": "",
            "periodo_academico": "",
            "periodo": None,
            "version_calendario": None,
            "semana_academica": None,
            "semana_academica_numero": None,
            "responsable_actividad": "",
            "origen_programacion": "no_aplica",
            "detalle_otro_proposito": "",
        }
        cotizacion = {
            "total": "0",
            "descuento_porcentaje": "0",
            "pertenencia_tarifaria": pertenencia_actual(self.usuario),
        }
        return ComandoCreacionReserva(
            actor=self.usuario,
            unidad=self.unidad,
            perfil_solicitante=self.usuario.profile,
            datos_solicitante_periodo={
                "institucion": "UPEC",
                "tipo_usuario": "estudiante",
                "facultad": "",
                "carrera": "",
                "nivel_academico": "",
            },
            contexto_actividad=contexto,
            tipo_solicitud="recursos",
            proposito="Investigación",
            proposito_codigo="investigacion_innovacion",
            frecuencia_reserva="unica",
            fechas_programadas=[date(2026, 10, 20)],
            fechas_omitidas=[],
            hora_inicio=time(9),
            hora_fin=time(11),
            duracion=2,
            horas=[9, 10],
            horas_seleccionadas_texto="[9, 10]",
            receta_proceso=None,
            producto_solicitado=None,
            factor_proceso=None,
            provision_consumibles="ninguno",
            incluye_espacio=True,
            solicito_espacio=True,
            solicito_equipo=False,
            solicito_software=False,
            alcance_espacio="espacio_unico",
            responsable=None,
            recursos=[],
            software=[],
            espacios=[],
            servicios=[],
            participantes=[],
            consumibles_a_registrar=[],
            archivos=[],
            indicaciones_archivos=[],
            guias_actividad=[],
            permisos_descarga_guias=[],
            solicita_publicacion_guias=False,
            modalidad_servicio="",
            materia_prima_cliente=False,
            cotizacion=cotizacion,
            cotizacion_aceptada=False,
            metodo_pago="",
            trabajo_servicio=None,
            piezas_por_sesion=1,
            detalle_trabajo="Prueba transaccional directa.",
            fecha_entrega_prevista=None,
            fin_servicio_programado=None,
            equipo_servicio=None,
            filas_cronograma=[],
            recursos_por_sesion={},
            asignatura=None,
            equipo_codigo="ESPACIO",
            equipo_nombre="Espacio de la unidad",
            titulo_solicitud="Reserva transaccional",
            descripcion="Reserva creada desde el caso de uso.",
            requisitos_especiales="",
            intencion_solicitud="Validar la escritura atómica del expediente.",
            institucion_solicitada="UPEC",
            siglas_institucion="UPEC",
            requiere_guia_integrada=False,
        )

    def test_crea_expediente_y_revision_sin_peticion_http(self):
        resultado = crear_expediente_reserva(
            self.comando(),
            completar_guia=lambda **_datos: self.fail("No debía completar guía"),
            auditar=lambda **_datos: None,
        )

        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(resultado.reserva.usuario, self.usuario)
        self.assertEqual(resultado.reserva.laboratorio, self.unidad)
        self.assertEqual(resultado.reservas_creadas, [resultado.reserva])
        self.assertTrue(
            RevisionReserva.objects.filter(reserva=resultado.reserva, numero=1).exists()
        )

    def test_fallo_tardio_revierte_todo_el_expediente(self):
        with patch(
            "apps.reservas.presentation.creacion_transaccion.crear_notificacion",
            side_effect=RuntimeError("fallo tardío sintético"),
        ):
            with self.assertRaisesMessage(RuntimeError, "fallo tardío sintético"):
                crear_expediente_reserva(
                    self.comando(),
                    completar_guia=lambda **_datos: None,
                    auditar=lambda **_datos: None,
                )

        self.assertFalse(Reserva.objects.exists())
        self.assertFalse(RevisionReserva.objects.exists())
