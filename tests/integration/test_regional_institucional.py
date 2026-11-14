import json
import io
from datetime import date, datetime, time, timezone as utc_timezone
import subprocess
import sys
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.template import engines
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.core.presentation.regional import regional_actual, regional_publica, validar_intervalo_institucional
from apps.core.checks import regional_configurada
from apps.core.regional import configuracion_regional, instante_civil, intervalo_civil
from config.regional import configuracion_regional_entorno
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad


class RegionalInstitucionalTests(SimpleTestCase):
    def test_upec_y_custom_sin_configuracion_no_cambian_fechas(self):
        for entorno in ({}, {"INSTITUTION_PROFILE": "custom"}):
            regional = configuracion_regional_entorno(entorno)
            self.assertEqual((regional.idioma, regional.zona_horaria), ("es-ec", "America/Guayaquil"))
        self.assertEqual(regional_actual().zona_horaria, "America/Guayaquil")

    @override_settings(TIME_ZONE="UTC", LANGUAGE_CODE="en-gb")
    def test_idioma_y_zona_propia_llegan_al_html_sin_modificar_literales(self):
        with timezone.override("America/Guayaquil"):
            reserva = Reserva(fecha=date(2026, 9, 16), hora_inicio=time(8), hora_fin=time(10))
            self.assertEqual(reserva.fecha_hora_inicio.utcoffset().total_seconds(), 0)
        configuracion = regional_publica()["regional_institucion"]
        self.assertEqual(configuracion, {"idioma": "en-gb", "zona_horaria": "UTC"})
        respuesta = engines["django"].get_template("base.html").render({}, RequestFactory().get("/"))
        self.assertIn('<html lang="en-gb">', respuesta)
        self.assertIn('"zona_horaria": "UTC"', respuesta)
        self.assertIn("regional_institucion.js", respuesta)

    @override_settings(TIME_ZONE="America/Bogota", LANGUAGE_CODE="es-co")
    def test_bogota_calendario_y_reporte_preservan_instantes_utc(self):
        instante = datetime(2026, 9, 16, 3, 30, tzinfo=utc_timezone.utc)
        self.assertEqual(regional_actual().idioma, "es-co")
        self.assertEqual(timezone.localdate(instante), date(2026, 9, 15))
        self.assertEqual(timezone.localtime(instante).strftime("%d/%m/%Y %H:%M"), "15/09/2026 22:30")
        self.assertEqual(instante.isoformat(), "2026-09-16T03:30:00+00:00")
        inicio, fin = validar_intervalo_institucional(datetime(2026, 9, 16, 8), datetime(2026, 9, 16, 10))
        self.assertEqual(inicio.astimezone(utc_timezone.utc).hour, 13)
        self.assertEqual((fin - inicio).total_seconds(), 7200)

    @override_settings(TIME_ZONE="Europe/Madrid", LANGUAGE_CODE="es")
    def test_madrid_rechaza_horas_inexistentes_duplicadas_y_salto(self):
        zona = ZoneInfo("Europe/Madrid")
        for inicio, fin in ((datetime(2027, 3, 28, 2), datetime(2027, 3, 28, 3)),
                            (datetime(2027, 10, 31, 2), datetime(2027, 10, 31, 3)),
                            (datetime(2027, 3, 28, 1), datetime(2027, 3, 28, 4))):
            with self.subTest(inicio=inicio), self.assertRaises(ValueError):
                intervalo_civil(inicio, fin, zona)
            reserva = Reserva(fecha=inicio.date(), hora_inicio=inicio.time(), hora_fin=fin.time(),
                              nombre_solicitante="Solicitante", correo_solicitante="prueba@example.test")
            with self.assertRaises(ValidationError) as error:
                reserva.clean()
            self.assertIn("hora_inicio", error.exception.message_dict)
        for mes, desplazamiento in ((1, 3600), (7, 7200)):
            inicio, _ = validar_intervalo_institucional(datetime(2027, mes, 15, 8), datetime(2027, mes, 15, 10))
            self.assertEqual(inicio.utcoffset().total_seconds(), desplazamiento)

    @override_settings(TIME_ZONE="Pacific/Auckland", LANGUAGE_CODE="en")
    def test_fecha_de_reserva_usa_zona_institucional_en_limite_de_dia(self):
        instante = datetime(2027, 1, 1, 23, tzinfo=utc_timezone.utc)
        reserva = Reserva(fecha=date(2027, 1, 2), hora_inicio=time(8), hora_fin=time(9),
                          nombre_solicitante="Solicitante", correo_solicitante="prueba@example.test")
        with patch("django.utils.timezone.now", return_value=instante):
            reserva.clean()
            reserva.fecha = date(2027, 1, 1)
            with self.assertRaises(ValidationError) as error:
                reserva.clean()
        self.assertIn("fecha", error.exception.message_dict)

    def test_configuraciones_invalidas_fallan_sin_aceptar_codigo_o_rutas(self):
        for idioma, zona in (("<script>", "UTC"), ("en-12", "UTC"), ("es", "../UTC"), ("es", "Zona/Inexistente"), (None, "UTC")):
            with self.subTest(idioma=idioma, zona=zona), self.assertRaises(ValueError):
                configuracion_regional(idioma, zona)
        with self.assertRaises(ImproperlyConfigured):
            configuracion_regional_entorno({"INSTITUTION_TIME_ZONE": ""})
        with self.assertRaises(ImproperlyConfigured):
            configuracion_regional_entorno({"INSTITUTION_LANGUAGE_CODE": "zz"})
        with override_settings(LANGUAGE_CODE="zz"):
            self.assertEqual(regional_configurada(None)[0].id, "slcid.E005")
        for cambios in ({"TIME_ZONE": "Zona/Inexistente"}, {"USE_TZ": False}):
            with self.subTest(cambios=cambios), override_settings(**cambios):
                self.assertIn("slcid.E005", {error.id for error in run_checks()})
        with self.assertRaises(ValueError):
            instante_civil(datetime(2026, 9, 16, tzinfo=utc_timezone.utc), ZoneInfo("UTC"))

    def test_navegador_en_otra_zona_elige_hoy_institucional_sin_desplazar_fecha_civil(self):
        programa = """
const fs = require('fs');
const vm = require('vm');
global.window = {};
global.document = {getElementById: () => ({textContent: JSON.stringify({idioma:'es-co', zona_horaria:'America/Bogota'})})};
vm.runInThisContext(fs.readFileSync('apps/core/static/portal/js/components/regional_institucion.js', 'utf8'));
const hoy = window.regionalInstitucion.hoy(new Date('2026-09-16T03:30:00Z'));
console.log(JSON.stringify({dia:hoy.getDate(),mes:hoy.getMonth()+1,idioma:window.regionalInstitucion.idioma}));
"""
        import os
        for zona_dispositivo in ("UTC", "Pacific/Auckland", "America/Los_Angeles"):
            resultado = subprocess.run(["node", "-e", programa], env={**os.environ, "TZ": zona_dispositivo},
                                       check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(resultado.stdout), {"dia": 15, "mes": 9, "idioma": "es-co"})

    def test_contrato_puro_no_importa_django(self):
        programa = "from apps.core.regional import configuracion_regional; import sys; configuracion_regional('en','UTC'); assert 'django' not in sys.modules"
        subprocess.run([sys.executable, "-c", programa], check=True, capture_output=True)


class AuditoriaRegionalTests(TestCase):
    def test_auditoria_cuenta_cambio_de_zona_sin_escrituras_ni_datos_personales(self):
        unidad = Unidad.objects.create(nombre="Unidad regional", slug="unidad-regional",
                                       dependencia="laboratorios", fecha_inicio=date(2026, 1, 1))
        reserva = Reserva.objects.create(laboratorio=unidad, fecha=date(2027, 9, 16),
                                          hora_inicio=time(8), hora_fin=time(10),
                                          nombre_solicitante="Nombre reservado", correo_solicitante="privado@example.test")
        antes = Reserva.objects.values().get(pk=reserva.pk)
        salida = io.StringIO()
        call_command("auditar_configuracion_regional", stdout=salida)
        self.assertIn("reservas_con_instante_distinto: 0", salida.getvalue())
        salida = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("auditar_configuracion_regional", zona_horaria="UTC", stdout=salida)
        self.assertIn("reservas_con_instante_distinto: 1", salida.getvalue())
        self.assertNotIn("Nombre reservado", salida.getvalue())
        self.assertNotIn("privado@", salida.getvalue())
        self.assertEqual(Reserva.objects.values().get(pk=reserva.pk), antes)
