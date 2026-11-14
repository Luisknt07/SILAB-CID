"""Activar y desactivar desde la gestión sin que nada desaparezca de sus listas.

Las áreas controlan su disponibilidad; cada recurso conserva de forma independiente su existencia y condición.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo, VideoEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea, ElementoFichaArea
from apps.gestion_unidades.models.interior import MedioInterior
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class ActivacionIndependienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-activacion', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio con áreas activables', slug='lab-activable',
                                           dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                           administrador=cls.gestor)
        cls.url = reverse('gestion_operacion_accion', args=[cls.unidad.slug])

    def setUp(self):
        self.client.force_login(self.gestor)
        self.rv = EspacioReservable.objects.create(unidad=self.unidad, codigo='ACT-AREA-RV', nombre='Realidad virtual',
                                                   capacidad=8, reservable=True)
        self.meta = EspacioReservable.objects.create(unidad=self.unidad, codigo='ACT-AREA-META', nombre='Metaverso',
                                                     capacidad=12, reservable=True)
        visor, torre = (EquiposServicios.objects.create(codigo='ACT-VR-01', nombre='Visor'),
                        EquiposServicios.objects.create(codigo='ACT-PC-01', nombre='Torre de simulación'))
        self.visor = UnidadEquipo.objects.create(codigo_unidad='ACT-VR-01-01', equipo=visor, laboratorio=self.unidad,
                                                 estado_unidad='en_uso')
        self.torre = UnidadEquipo.objects.create(codigo_unidad='ACT-PC-01-01', equipo=torre, laboratorio=self.unidad)
        self.compartido = UnidadEquipo.objects.create(codigo_unidad='ACT-VR-01-02', equipo=visor, laboratorio=self.unidad)
        self.rv.equipos_asociados.add(self.visor, self.torre, self.compartido)
        self.meta.equipos_asociados.add(self.compartido)
        self.unity = SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Unity', licencias_totales=5,
                                                       licencias_disponibles=5)
        self.unity.equipos_instalados.add(self.torre)
        self.mascaras = Consumible.objects.create(unidad=self.unidad, codigo='ACT-MASC', nombre='Máscaras',
                                                  unidad_medida='u', visible_en_reservas=True)
        self.cable = Consumible.objects.create(unidad=self.unidad, codigo='ACT-CABLE', nombre='Cable', unidad_medida='u')
        ConsumiblePorEquipo.objects.create(consumible=self.cable, equipo=torre)
        # Las máscaras también las usa el visor que sigue activo en Metaverso: no se desactivan.
        ConsumiblePorEquipo.objects.create(consumible=self.mascaras, equipo=visor)

    def alternar(self, **datos):
        return self.client.post(self.url, {'accion': 'alternar', **datos})

    def recargar(self, *objetos):
        for objeto in objetos:
            objeto.refresh_from_db()

    def test_area_no_altera_existencia_o_condicion_de_los_recursos(self):
        respuesta = self.alternar(modulo='recursos', entidad='espacio', registro_id=self.rv.pk)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.recargar(self.rv, self.visor, self.torre, self.compartido, self.unity, self.cable, self.mascaras)
        self.assertEqual((self.rv.activo, self.rv.reservable), (False, False))
        self.assertTrue(all([self.visor.activa, self.torre.activa, self.compartido.activa,
            self.unity.activo, self.cable.activo, self.mascaras.activo]))
        self.assertEqual(self.visor.estado_unidad, 'en_uso')
        self.alternar(modulo='recursos', entidad='espacio', registro_id=self.rv.pk)
        self.recargar(self.rv, self.visor)
        self.assertEqual((self.rv.activo, self.rv.reservable, self.visor.estado_unidad), (True, True, 'en_uso'))

    def test_editar_area_inactiva_no_desactiva_sus_existencias(self):
        self.client.post(self.url, {'modulo': 'recursos', 'entidad': 'espacio', 'registro_id': self.rv.pk,
                                    'codigo': self.rv.codigo, 'nombre': self.rv.nombre, 'capacidad': '8',
                                    'reservable': 'on', 'equipos_asociados': [self.visor.pk, self.torre.pk, self.compartido.pk]})
        self.recargar(self.rv, self.torre)
        self.assertEqual((self.rv.activo, self.torre.activa), (False, True))

    def test_lo_desactivado_por_su_cuenta_no_vuelve_con_el_area(self):
        self.alternar(modulo='recursos', entidad='equipo', registro_id=self.torre.pk)
        self.alternar(modulo='consumible', registro_id=self.cable.pk)
        self.recargar(self.torre, self.cable)
        self.assertEqual((self.torre.activa, self.cable.activo), (False, False))
        self.alternar(modulo='recursos', entidad='espacio', registro_id=self.rv.pk)
        self.alternar(modulo='recursos', entidad='espacio', registro_id=self.rv.pk)
        self.recargar(self.torre, self.cable, self.visor)
        self.assertEqual((self.torre.activa, self.cable.activo, self.visor.activa), (False, False, True))
        # Cada uno se reactiva con su propio interruptor.
        self.alternar(modulo='recursos', entidad='software', registro_id=self.unity.pk)
        self.unity.refresh_from_db()
        self.assertFalse(self.unity.activo)
        self.alternar(modulo='recursos', entidad='equipo', registro_id=self.torre.pk)
        self.torre.refresh_from_db()
        self.assertEqual((self.torre.activa, self.torre.estado_unidad), (True, 'disponible'))


class VideosPrecargadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-videos', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de videos', slug='lab-videos', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2026, 1, 1), administrador=cls.gestor)
        familia = FamiliaEquipo.objects.create(nombre='Escáneres LiDAR', slug='escaneres-lidar', grupo='Captura')
        VideoEquipo.objects.create(familia=familia, url='https://youtu.be/aaaaaaaaaaa', titulo='Escaneo | BIM', canal='BIM')
        tipo = EquiposServicios.objects.create(codigo='VID-LID-01', nombre='iPad con LiDAR', familia=familia)
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='VID-LID-01-01', equipo=tipo, laboratorio=cls.unidad)
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='VID-AREA-RA', nombre='Realidad aumentada',
                                                    capacidad=6)
        ficha = FichaArea.objects.create(espacio=cls.area, que_es='.', fuente='Prueba')
        ElementoFichaArea.objects.create(ficha=ficha, tipo='video', nombre='¿Qué es la RA? | Domestika',
                                         url='https://www.youtube.com/watch?v=bbbbbbbbbbb', para_que='Explica la RA.')

    def setUp(self):
        self.client.force_login(self.gestor)

    def test_el_equipo_precarga_los_videos_de_su_tipo(self):
        url = reverse('editar_equipo_ficha', args=[self.unidad.slug, self.equipo.codigo_unidad])
        editor = self.client.get(url, {'seccion': 'videos', 'fragmento': '1'})
        self.assertContains(editor, 'https://youtu.be/aaaaaaaaaaa | Escaneo · BIM | BIM')
        self.assertContains(editor, 'data-editor-videos')
        self.assertContains(editor, 'Precargados con los videos de su tipo de equipo')

    def test_el_area_precarga_su_referencia_y_lo_guardado_la_reemplaza(self):
        url = reverse('editar_area', args=[self.unidad.slug, self.area.codigo])
        editor = self.client.get(url, {'seccion': 'videos', 'fragmento': '1'})
        self.assertContains(editor, 'https://www.youtube.com/watch?v=bbbbbbbbbbb | ¿Qué es la RA? · Domestika | Explica la RA.')
        self.assertContains(editor, 'Precargados con los videos de referencia del área')
        self.client.post(url, {'seccion': 'videos', 'videos': 'https://youtu.be/ccccccccccc | Recorrido | Visita'})
        self.assertEqual(list(MedioInterior.objects.filter(espacio=self.area, tipo='video').values_list('titulo', flat=True)),
                         ['Recorrido'])
        pagina = self.client.get(reverse('area_unidad', args=[self.unidad.slug, self.area.codigo])).content.decode()
        self.assertIn('ccccccccccc', pagina)
        self.assertNotIn('bbbbbbbbbbb', pagina, 'Los videos guardados reemplazan a los de referencia.')
