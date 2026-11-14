"""Toda actividad docente exige guía y los subtipos viven en su propósito."""

import os

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from apps.reservas.models.reservas import SUBTIPO_ACTIVIDAD_CHOICES, SUBTIPOS_POR_PROPOSITO


class SubtiposPorPropositoTests(SimpleTestCase):
    def test_docencia_agrupa_solo_actividades_con_guia(self):
        self.assertEqual(SUBTIPOS_POR_PROPOSITO['docencia_practica'], {
            'practica_curricular', 'simulacion_demostracion', 'practica_evaluativa',
            'proyecto_asignatura', 'taller_docente',
        })
        self.assertIn('investigacion_formativa', SUBTIPOS_POR_PROPOSITO['investigacion_innovacion'])
        self.assertIn('entrenamiento_tecnico', SUBTIPOS_POR_PROPOSITO['capacitacion'])
        codigos = {codigo for codigo, _ in SUBTIPO_ACTIVIDAD_CHOICES}
        for subtipos in SUBTIPOS_POR_PROPOSITO.values():
            self.assertTrue(subtipos <= codigos, subtipos - codigos)

    def test_el_asistente_usa_el_mismo_mapa_y_abre_equipos_sin_areas(self):
        ruta = os.path.join(settings.BASE_DIR, 'apps', 'reservas', 'static', 'portal', 'js', 'pages', 'unidades', 'reservas', 'reservation_wizard.js')
        with open(ruta, encoding='utf-8') as archivo:
            js = archivo.read()
        for codigo, etiqueta in SUBTIPO_ACTIVIDAD_CHOICES:
            self.assertIn(f"['{codigo}', gettext('{etiqueta}')]", js, codigo)
        self.assertNotIn('guideIsOptionalHere', js)
        self.assertIn("const curricularPractice = directTeachingFlow && Boolean(subtypeSelect?.value);", js)
        self.assertIn("catalogInput.disabled = !directTeachingFlow || !hasApprovedGuide;", js)
        self.assertIn("if (!spaceInputs.length) return true;", js)


class DatosDePruebaTests(TestCase):
    def test_el_comando_declara_compatibilidad_por_equipo(self):
        from apps.laboratorios.operacion.management.commands.cargar_pruebas_fablab import Command

        codigos_insumos = {datos['codigo'] for datos in Command.CONSUMIBLES}
        codigos_equipos = {datos['codigo'] for datos in Command.EQUIPOS}
        for consumible, equipos, cantidad in Command.COMPATIBILIDAD_EQUIPOS:
            self.assertIn(consumible, codigos_insumos)
            self.assertTrue(set(equipos) <= codigos_equipos, equipos)
            self.assertGreater(float(cantidad), 0)
        fdm = next(datos for datos in Command.EQUIPOS if datos['codigo'] == 'FAB-EQ-FDM')
        self.assertEqual(len(fdm['unidades']), 3)
        # Todo software esta ligado a un equipo: se elige dentro de su tarjeta.
        self.assertTrue(all(datos['equipos_instalados'] for datos in Command.SOFTWARE))
        self.assertTrue(all(Command.FICHA_INSUMOS.get(datos['codigo'], {}).get('marca') for datos in Command.CONSUMIBLES))

    def test_las_reservas_de_ejemplo_cubren_los_casos_de_la_cascada(self):
        from apps.laboratorios.operacion.management.commands.cargar_pruebas_fablab import Command

        codigos_equipos = {datos['codigo'] for datos in Command.EQUIPOS}
        codigos_espacios = {datos['codigo'] for datos in Command.ESPACIOS}
        software = {datos['codigo']: datos for datos in Command.SOFTWARE}
        codigos_insumos = {datos['codigo'] for datos in Command.CONSUMIBLES}
        estados = set()
        for datos in Command.RESERVAS_EJEMPLO:
            with self.subTest(reserva=datos['titulo']):
                if datos['equipo']:
                    self.assertIn(datos['equipo'], codigos_equipos)
                self.assertTrue(set(datos['espacios']) <= codigos_espacios, datos['espacios'])
                self.assertTrue(set(datos['software']) <= set(software), datos['software'])
                self.assertTrue({codigo for codigo, _ in datos['consumibles']} <= codigos_insumos)
                estados.add(datos['estado'])
        self.assertTrue({'pendiente', 'confirmada', 'rechazada', 'cancelada'} <= estados)
        # Un caso con programa propio obligatorio, uno con software adicional y una sala sola.
        self.assertTrue(any(
            software[codigo].get('uso_en_equipo') == 'obligatorio'
            for datos in Command.RESERVAS_EJEMPLO for codigo in datos['software']
        ))
        self.assertTrue(any('Software adicional' in datos.get('requisitos_especiales', '') for datos in Command.RESERVAS_EJEMPLO))
        self.assertTrue(any(datos['equipo'] is None for datos in Command.RESERVAS_EJEMPLO))
