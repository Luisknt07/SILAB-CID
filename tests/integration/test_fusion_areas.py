"""Fusión de áreas: la que se integra pasa a la otra sus equipos, su ficha y sus fotos, queda inactiva señalando
adónde fue, su página lleva a la nueva y los cargadores no la vuelven a crear ni a llenar."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.fusion_areas import area_vigente, fusionar_area, integrada
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.interior import MedioInterior
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class FusionDeAreasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de fusión', slug='laboratorio-fusion',
                                           dependencia='laboratorios', descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.destino = EspacioReservable.objects.create(unidad=cls.unidad, codigo='FUS-AREA-LASER', nombre='Láser',
                                                       capacidad=4, orden=1)
        cls.origen = EspacioReservable.objects.create(unidad=cls.unidad, codigo='FUS-AREA-CNC', nombre='CNC',
                                                      capacidad=3, orden=2)
        modelo = EquiposServicios.objects.create(codigo='FUS-EQ-CNC', nombre='Fresadora CNC')
        cls.fresadora = UnidadEquipo.objects.create(codigo_unidad='FUS-CNC-01', equipo=modelo, laboratorio=cls.unidad)
        cls.origen.equipos_asociados.add(cls.fresadora)
        laser = FichaArea.objects.create(espacio=cls.destino, que_es='Corte con luz.', aplicaciones='Grabado')
        ElementoFichaArea.objects.create(ficha=laser, tipo='equipo', nombre='Cortadora láser', orden=1)
        cnc = FichaArea.objects.create(espacio=cls.origen, que_es='Fresado de piezas.', aplicaciones='Moldes')
        ElementoFichaArea.objects.create(ficha=cnc, tipo='equipo', nombre='Fresadora CNC', orden=1)
        MedioInterior.objects.create(unidad=cls.unidad, espacio=cls.origen, titulo='La fresadora')

    def test_fusion_traslada_todo_y_deja_el_area_integrada(self):
        resumen = fusionar_area(self.origen, self.destino)
        self.assertEqual((resumen['equipos'], resumen['fotos'], resumen['fichas']), (1, 1, 1))
        self.origen.refresh_from_db()
        self.assertEqual((self.origen.activo, self.origen.reservable, self.origen.integrada_en), (False, False, self.destino))
        self.assertEqual(list(self.destino.equipos_asociados.all()), [self.fresadora])
        self.assertFalse(self.origen.equipos_asociados.exists())
        ficha = FichaArea.objects.get(espacio=self.destino)
        self.assertEqual(list(ficha.elementos.values_list('nombre', 'orden')), [('Cortadora láser', 1), ('Fresadora CNC', 2)])
        self.assertEqual((ficha.que_es, ficha.aplicaciones), ('Corte con luz.\nFresado de piezas.', 'Grabado\nMoldes'))
        self.assertFalse(FichaArea.objects.filter(espacio=self.origen).exists())
        self.assertEqual(MedioInterior.objects.get().espacio, self.destino)
        self.assertEqual((area_vigente(self.origen), integrada(self.unidad, 'FUS-AREA-CNC')), (self.destino, self.origen))
        # Repetirla no duplica nada.
        self.assertEqual(fusionar_area(self.origen, self.destino), {})
        with self.assertRaises(ValueError):
            fusionar_area(self.destino, self.destino)

    def test_la_pagina_del_area_integrada_lleva_a_la_nueva(self):
        fusionar_area(self.origen, self.destino)
        respuesta = self.client.get(reverse('area_unidad', args=[self.unidad.slug, 'FUS-AREA-CNC']))
        self.assertRedirects(respuesta, reverse('area_unidad', args=[self.unidad.slug, 'FUS-AREA-LASER']),
                             fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('area_unidad', args=[self.unidad.slug, 'FUS-NO-EXISTE'])).status_code,
                         404)

    def test_no_invierte_una_fusion_aunque_los_objetos_esten_desactualizados(self):
        fusionar_area(self.origen, self.destino)
        with self.assertRaisesMessage(ValueError, 'destino activa'):
            fusionar_area(self.destino, self.origen)
        self.destino.refresh_from_db()
        self.assertIsNone(self.destino.integrada_en)

    def test_un_ciclo_historico_falla_cerrado_sin_colgar_la_ficha(self):
        EspacioReservable.objects.filter(pk=self.origen.pk).update(integrada_en=self.destino, activo=False)
        EspacioReservable.objects.filter(pk=self.destino.pk).update(integrada_en=self.origen, activo=False)
        self.origen.refresh_from_db()
        self.assertIsNone(area_vigente(self.origen))
        self.assertEqual(self.client.get(reverse('area_unidad', args=[self.unidad.slug, self.origen.codigo])).status_code, 404)

    def test_no_redirige_un_area_historica_a_otra_unidad(self):
        otra = Unidad.objects.create(nombre='Otra unidad', slug='otra-fusion', descripcion='.', fecha_inicio=date(2020, 1, 1))
        ajena = EspacioReservable.objects.create(unidad=otra, codigo='OTRA', nombre='Ajena')
        EspacioReservable.objects.filter(pk=self.origen.pk).update(integrada_en=ajena)
        self.origen.refresh_from_db()
        self.assertIsNone(area_vigente(self.origen))


class ReformaDeAreasTests(TestCase):
    """La reforma aplica las áreas nuevas: renombra, crea las que faltan, fusiona las absorbidas y es repetible."""

    def test_reforma_fusiona_las_areas_absorbidas_y_es_repetible(self):
        call_command('reorganizar_unidades', stdout=StringIO())
        logistica = Unidad.objects.get(slug='laboratorio-logistica-comercio-internacional')
        activas = list(logistica.espacios_reservables.filter(activo=True).order_by('orden').values_list('nombre', flat=True))
        self.assertEqual(activas, [
            'Almacenamiento e intralogística inteligente', 'Planificación de la cadena de suministro',
            'Transporte, distribución y movilidad', 'Logística de producción y operaciones',
            'Logística internacional y operaciones de comercio exterior', 'Tecnologías aplicadas y simulación logística',
        ])
        sala = logistica.espacios_reservables.get(codigo='LOG-SALA-NEGOCIACION') if logistica.espacios_reservables.filter(
            codigo='LOG-SALA-NEGOCIACION').exists() else None
        if sala is not None:
            self.assertEqual((sala.activo, sala.integrada_en.codigo), (False, 'LOG-AREA-COMERCIO'))
        produccion = logistica.espacios_reservables.get(codigo='LOG-AREA-PRODUCCION')
        self.assertTrue(produccion.descripcion_publica.startswith('Flujo de materiales'))
        energias = Unidad.objects.get(slug='laboratorio-energias-renovables-territorio')
        self.assertIn('Titular: Turismo (hasta el cierre de la carrera)', energias.carreras)
        salida = StringIO()
        call_command('reorganizar_unidades', stdout=salida)
        self.assertNotIn('Fusionada', salida.getvalue())
