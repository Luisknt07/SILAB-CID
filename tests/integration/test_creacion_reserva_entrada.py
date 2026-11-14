from django.http import QueryDict
from django.test import SimpleTestCase

from apps.reservas.presentation.creacion_entrada import normalizar_entrada_basica, normalizar_intervalo, normalizar_proposito, validar_intencion_solicitud


def entrada_valida(**cambios):
    datos = {
        "unidad_id": "15",
        "tipo_solicitud": "recursos",
        "provision_consumibles": "ninguno",
        "piezas_por_sesion": "2",
        "incluye_espacio": "1",
        "cotizacion_aceptada": "on",
        "aceptar_terminos": "sí",
        "proposito_codigo": "investigacion_innovacion",
        "fecha_inicio": "2026-10-20T09:00",
        "fecha_fin": "2026-10-20T11:00",
        "horas_seleccionadas": "[9, 10]",
    }
    datos.update(cambios)
    return QueryDict("", mutable=True).copy() | datos


class EntradaBasicaReservaTests(SimpleTestCase):
    def test_normaliza_campos_sin_conocer_http_o_la_base(self):
        entrada = normalizar_entrada_basica(entrada_valida())

        self.assertEqual(entrada.unidad_id, "15")
        self.assertEqual(entrada.tipo_solicitud, "recursos")
        self.assertEqual(entrada.piezas_por_sesion, 2)
        self.assertTrue(entrada.incluye_espacio_solicitado)
        self.assertTrue(entrada.cotizacion_aceptada)
        self.assertEqual(entrada.proposito_codigo, "investigacion_innovacion")

    def test_conserva_el_alias_historico_del_proposito(self):
        codigo, etiqueta = normalizar_proposito("Investigación")

        self.assertEqual(codigo, "investigacion_innovacion")
        self.assertTrue(etiqueta)

    def test_rechaza_tipo_provision_y_terminos_invalidos(self):
        casos = (
            ({"tipo_solicitud": "desconocida"}, "tipo de solicitud"),
            ({"provision_consumibles": "propios"}, "cómo se cubrirán"),
            ({"aceptar_terminos": ""}, "Acepta las condiciones"),
        )
        for cambios, mensaje in casos:
            with self.subTest(cambios=cambios):
                with self.assertRaisesMessage(ValueError, mensaje):
                    normalizar_entrada_basica(entrada_valida(**cambios))

    def test_intencion_aplica_limites_distintos_para_descripcion_breve(self):
        with self.assertRaisesMessage(ValueError, "al menos 30 palabras"):
            validar_intencion_solicitud("breve " * 29, breve=True)
        with self.assertRaisesMessage(ValueError, "hasta 150 palabras"):
            validar_intencion_solicitud("larga " * 151, breve=True)
        self.assertEqual(
            validar_intencion_solicitud("válida " * 30, breve=True),
            "válida " * 30,
        )


class IntervaloReservaTests(SimpleTestCase):
    def test_convierte_horas_consecutivas_en_intervalo_local(self):
        datos = entrada_valida()

        intervalo = normalizar_intervalo(
            datos,
            datos["fecha_inicio"],
            datos["fecha_fin"],
        )

        self.assertEqual(intervalo.horas, [9, 10])
        self.assertEqual(intervalo.hora_inicio.hour, 9)
        self.assertEqual(intervalo.hora_fin.hour, 11)
        self.assertEqual(intervalo.duracion, 2)

    def test_rechaza_offsets_y_horas_no_consecutivas(self):
        casos = (
            (
                entrada_valida(
                    fecha_inicio="2026-10-20T09:00-05:00",
                    fecha_fin="2026-10-20T11:00-05:00",
                ),
                "sin desplazamiento UTC",
            ),
            (entrada_valida(horas_seleccionadas="[9, 11]"), "bloques consecutivos"),
        )
        for datos, mensaje in casos:
            with self.subTest(mensaje=mensaje):
                with self.assertRaisesMessage(ValueError, mensaje):
                    normalizar_intervalo(
                        datos,
                        datos["fecha_inicio"],
                        datos["fecha_fin"],
                    )

    def test_rechaza_json_ambiguo_con_el_contrato_historico(self):
        datos = entrada_valida(horas_seleccionadas="no-json")

        with self.assertRaisesMessage(ValueError, "Formato de fecha inválido"):
            normalizar_intervalo(
                datos,
                datos["fecha_inicio"],
                datos["fecha_fin"],
            )
