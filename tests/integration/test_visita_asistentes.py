import json

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.reservas.presentation.asistentes_visita import asistentes_desde_json
from tests.integration import test_visitas_calendario as escenarios
from tests.integration.test_visitas import BaseVisitas


def fila(**extra):
    return {'nombre': 'Ana Pérez', 'documento': '0012345678', 'rol': 'estudiante',
            'telefono': '+593 999 123 456', 'correo': 'ana@example.org', **extra}


class ValidacionTablaVisitaTests(SimpleTestCase):
    def test_preserva_documentos_con_ceros_y_todos_los_campos(self):
        result = asistentes_desde_json(json.dumps([fila(nombre=' Ana Pérez ')]))
        self.assertEqual(result, [fila()])

    def test_ignora_filas_completamente_vacias(self):
        self.assertEqual(asistentes_desde_json(json.dumps([{}, fila()])), [fila()])

    def test_rechaza_correo_rol_nombre_o_documento_duplicado(self):
        for rows in ([fila(correo='correo-invalido')], [fila(rol='inventado')], [fila(nombre='')], [fila(), fila(nombre='Otra persona')]):
            with self.subTest(rows=rows), self.assertRaises(ValidationError):
                asistentes_desde_json(json.dumps(rows))

    def test_rechaza_formatos_rotos_y_limites_sin_recortar_informacion(self):
        for payload in ('[', '{}', json.dumps([fila(nombre='x' * 151)]), json.dumps([fila()] * 201)):
            with self.subTest(payload=payload[:30]), self.assertRaises(ValidationError):
                asistentes_desde_json(payload)


class GuardadoTablaVisitaTests(BaseVisitas):
    enviar = escenarios.VisitasEnAsistenteUnicoTests.enviar
    calendario = escenarios.VisitasEnAsistenteUnicoTests.calendario
    def test_tabla_guarda_rol_y_contactos_con_conteo_automatico_revalidado(self):
        response = self.enviar(visita_personas='199', visita_conteo='lista',
                               visita_asistentes_json=json.dumps([fila(), fila(nombre='Profesor Uno', documento='AA-123', rol='docente', correo='profe@example.org')]))
        self.assertTrue(response.json()['success'], response.content)
        from apps.reservas.models.visitas import SolicitudVisita
        visita = SolicitudVisita.objects.get(pk=response.json()['visita_id'])
        self.assertEqual(visita.personas, 2)
        self.assertEqual(visita.reserva.numero_participantes, 2)
        self.assertEqual(visita.rango_edades, '')
        self.assertEqual(list(visita.asistentes.values('nombre', 'documento', 'rol', 'telefono', 'correo'))[0], fila())

    def test_cantidad_estimada_con_lista_pendiente_sigue_permitida(self):
        response = self.enviar(visita_conteo='estimado', visita_personas='4', visita_asistentes_json='[]')
        self.assertTrue(response.json()['success'], response.content)

    def test_conteo_automatico_vacio_y_tabla_invalida_no_guardan(self):
        from apps.reservas.models.visitas import SolicitudVisita
        for payload in ('[]', '[', json.dumps([fila(correo='sin-arroba')])):
            response = self.enviar(visita_conteo='lista', visita_asistentes_json=payload)
            self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(SolicitudVisita.objects.exists())

    def test_contactos_solo_se_muestran_en_la_lista_de_asistencia_autorizada(self):
        response = self.enviar(visita_conteo='lista', visita_asistentes_json=json.dumps([fila()]))
        result = response.json()
        self.assertTrue(result['success'], response.content)
        from django.urls import reverse
        self.client.force_login(self.coordinacion)
        url = reverse('asistencia_visita', args=[self.unidad.slug, result['visita_id']])
        asistencia = self.client.get(url)
        self.assertContains(asistencia, 'ana@example.org')
        self.assertContains(asistencia, '+593 999 123 456')
        self.assertContains(asistencia, 'Estudiante')
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertNotContains(self.calendario(), 'ana@example.org')
