"""Datos técnicos de referencia de los equipos: validan la planta sin parecer medidos.

La carga llena capacidad, tiempos, consumos, dimensiones, confiabilidad y
coordenadas de cada equipo, marcados «valores de referencia, por verificar»; con
ellos se calculan la capacidad, el recorrido y los servicios industriales. Nunca
pisan un levantamiento validado ni un dato cargado a mano.
"""
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.completitud import tablero_unidad
from apps.plantas_piloto.operacion.presentation.diagramas import diagrama_recorrido
from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta
from apps.plantas_piloto.operacion.presentation.servicios_industriales import servicios_industriales
from apps.plantas_piloto.operacion.management.plantas.referencia_equipos import EQUIPOS
from apps.recursos.models.equipos import EquiposServicios
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.directorio_unidades.models.core import Unidad


class DatosDeReferenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        cls.unidad = Unidad.objects.get(slug='planta-piloto-lacteos')

    def equipos(self):
        return EquiposServicios.objects.filter(unidades__laboratorio=self.unidad).distinct()

    def test_cada_equipo_trae_sus_datos_de_referencia_marcados(self):
        for equipo in self.equipos():
            with self.subTest(equipo=equipo.codigo):
                self.assertIn(equipo.codigo, EQUIPOS)
                self.assertEqual(equipo.origen_datos_tecnicos, 'referencia')
                self.assertEqual(equipo.campos_criticos_vacios, [])

    def test_con_ellos_se_dibuja_el_recorrido_y_se_desbloquea_la_capacidad(self):
        receta = Receta.objects.get(codigo='LAC-REC-QUESO-100')
        self.assertIsNotNone(diagrama_recorrido(datos_de_receta(receta)))
        tablero = tablero_unidad(self.unidad)
        self.assertEqual(tablero['bloqueos'], [])
        secciones = {fila['numero']: fila for pestana in tablero['pestanas'] for fila in pestana['secciones']}
        self.assertEqual(secciones['1.3']['publicado'], secciones['1.3']['esperado'])
        self.assertEqual(secciones['3.4']['publicado'], secciones['3.4']['esperado'])
        self.assertEqual(secciones['3.3']['publicado'], servicios_industriales(self.unidad)['con_datos'])

    def test_no_pisa_un_levantamiento_validado_ni_un_dato_cargado_a_mano(self):
        pasteurizador = EquiposServicios.objects.get(codigo='LAC-EQ-PASTEUR')
        pasteurizador.origen_datos_tecnicos = 'medido'
        pasteurizador.capacidad_util_max = Decimal('250')
        pasteurizador.save()
        tina = EquiposServicios.objects.get(codigo='LAC-EQ-TINA')
        EquiposServicios.objects.filter(pk=tina.pk).update(
            origen_datos_tecnicos='', capacidad_util_max=Decimal('280'), potencia_kw=None,
        )
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        pasteurizador.refresh_from_db()
        tina.refresh_from_db()
        self.assertEqual(pasteurizador.origen_datos_tecnicos, 'medido')
        self.assertEqual(pasteurizador.capacidad_util_max, Decimal('250'))
        # Sin origen declarado solo se llena lo vacío.
        self.assertEqual(tina.capacidad_util_max, Decimal('280'))
        self.assertIsNotNone(tina.potencia_kw)
        self.assertEqual(tina.origen_datos_tecnicos, 'referencia')

    def test_la_pagina_de_servicios_y_su_documento(self):
        servicios = servicios_industriales(self.unidad)
        claves = {servicio['clave'] for servicio in servicios['servicios'] if servicio['filas']}
        self.assertEqual(claves, {'electricidad', 'vapor', 'agua', 'aire', 'frio', 'efluentes'})
        vapor = next(servicio for servicio in servicios['servicios'] if servicio['clave'] == 'vapor')
        self.assertIn('Caldera de vapor', vapor['nota'])
        url = reverse('servicios_industriales', args=[self.unidad.slug])
        pagina = self.client.get(url)
        self.assertContains(pagina, 'ENERGÍA ELÉCTRICA')
        self.assertContains(pagina, 'EFLUENTES Y AGUAS RESIDUALES')
        self.assertContains(pagina, 'valores de referencia, por verificar en planta')
        documento = self.client.get(f'{url}?formato=pdf')
        self.assertEqual(documento['Content-Type'], 'application/pdf')
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, url)

    def test_la_ficha_del_equipo_avisa_que_son_de_referencia(self):
        pagina = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, 'LAC-EQP-PAST-01']))
        self.assertContains(pagina, 'valores de referencia, por verificar en planta')
        self.assertContains(pagina, 'consumo de referencia')
