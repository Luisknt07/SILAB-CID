"""La mejora distingue actividad propia verificada, programación y falta de medición."""
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.presentation.mejora_continua import (
    actividad_efectiva, cumplimiento_del_periodo, pdf_de_mejora_continua,
)


class ActividadPropiaTests(SimpleTestCase):
    def unidad(self, tipo):
        return SimpleNamespace(dependencia=tipo, codigo_base=tipo)

    def test_fuentes_propias_verificadas_acreditan_actividad_sin_reservas(self):
        for tipo, clave in (('plantas_piloto', 'gestion_produccion'),
                            ('plantas_piloto', 'gestion_control_calidad'),
                            ('centro_experimental', 'gestion_ensayos'),
                            ('observatorios', 'gestion_boletines'),
                            ('observatorios', 'gestion_datos_actualizados'),
                            ('observatorios', 'gestion_eventos')):
            with self.subTest(tipo=tipo, fuente=clave):
                self.assertTrue(actividad_efectiva(self.unidad(tipo), {clave: 1})['hay_actividad'])

    def test_programar_no_acredita_ejecucion_ni_actividad_de_otro_perfil(self):
        datos = dict(sesiones=3, practicas_planificadas=2, produccion_planificada=5,
                     gestion_boletines=0, gestion_datos_actualizados=0, gestion_eventos=0,
                     gestion_produccion=1)
        lectura = actividad_efectiva(self.unidad('observatorios'), datos)
        self.assertFalse(lectura['hay_actividad'])
        self.assertFalse(lectura['perfil_pendiente'])

    def test_ausencia_de_medicion_no_se_interpreta_como_cero_verificado(self):
        self.assertTrue(actividad_efectiva(self.unidad('observatorios'), {})['perfil_pendiente'])
        self.assertFalse(actividad_efectiva(self.unidad('laboratorios'), {})['perfil_pendiente'])


class MejoraPorPerfilTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.unidad = Unidad.objects.create(nombre='Observatorio de prueba de actividad',
            slug='qa-observatorio-actividad-mejora', dependencia='observatorios',
            fecha_inicio=date(2024, 1, 1))

    def registros(self, **datos):
        return dict(sesiones=0, atendidas=0, horas=0, usuarios=0, practicas=0, servicios=0,
                    mantenimientos=0, mantenimientos_programados=0, incidencias=0,
                    gestion_boletines=0, gestion_datos_actualizados=0, gestion_eventos=0, **datos)

    def lectura(self, datos):
        with patch('apps.documentos.presentation.expediente_redaccion.registros_del_periodo', return_value=datos):
            return cumplimiento_del_periodo(self.unidad, 2025, 'A', hoy=date(2026, 10, 20))

    def test_publicacion_verificada_evita_dictamen_incorrecto_de_inactividad(self):
        datos = self.registros()
        datos['gestion_boletines'] = 1
        lectura = self.lectura(datos)
        self.assertFalse(lectura['sin_uso'])
        self.assertFalse(lectura['sin_uso_al_cierre'])
        self.assertFalse(lectura['requiere_mejora'])
        pdf = PdfReader(BytesIO(pdf_de_mejora_continua(lectura)))
        texto = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        self.assertIn('SLCID-OBS-INCUMPL', texto)
        self.assertIn('Publicaciones con revisión técnica', ' '.join(texto.split()))
        self.assertNotIn('Prácticas ejecutadas', texto)
        self.assertNotIn('versión firmada electrónicamente', texto)

    def test_solo_cero_con_medicion_disponible_origina_alerta_de_inactividad(self):
        datos = self.registros()
        medido = self.lectura(datos)
        self.assertTrue(medido['sin_uso_al_cierre'])
        self.assertTrue(medido['requiere_mejora'])
        for clave in ('gestion_boletines', 'gestion_datos_actualizados', 'gestion_eventos'):
            datos.pop(clave)
        pendiente = self.lectura(datos)
        self.assertTrue(pendiente['actividad_perfil_pendiente'])
        self.assertFalse(pendiente['sin_uso_al_cierre'])
        self.assertFalse(pendiente['requiere_mejora'])
