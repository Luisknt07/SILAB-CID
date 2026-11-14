"""Componentes, modos de uso y sistema de los equipos.

Cada componente lleva su cantidad, su tipo (viene con el equipo, complemento o repuesto) y para qué sirve; lo que el
modelo no registra lo completa su familia sin repetir lo que ya nombra. Los modos explican cómo funciona (autónomo,
con PC…) con lo que necesita, la versión del sistema es de cada unidad y los videos usan el reproductor de las áreas.
"""
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.plantillas_ficha import accesorios_de, ficha_estandar
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo, VideoEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

MODOS = [
    {'nombre': 'Autónomo', 'icono': 'fas fa-vr-cardboard', 'descripcion': 'Funciona sin cables con su propio procesador y batería.',
     'aplicaciones': ['Recorridos virtuales', 'Simulaciones de práctica'], 'requisitos': ['Espacio libre de 2 × 2 m', 'Red Wi-Fi']},
    {'nombre': 'Conectado a una PC', 'icono': 'fas fa-desktop', 'descripcion': 'La computadora procesa la imagen y el visor la muestra.',
     'aplicaciones': ['SteamVR', 'Desarrollo en Unity'], 'requisitos': ['Tarjeta gráfica NVIDIA RTX 3060 o superior', '16 GB de RAM']},
]


class ComponentesDelEquipoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.familia = FamiliaEquipo.objects.create(
            nombre='Visores de prueba', slug='visores-prueba', grupo='Realidad extendida', sistema='Sistema propio del visor.',
            componentes=[{'tipo': 'incluido', 'cantidad': 2, 'nombre': 'Controles táctiles', 'uso': 'Se emparejan al encender.'},
                         {'tipo': 'complementario', 'cantidad': 1, 'nombre': 'Cable de enlace de 3 m', 'uso': 'Conecta el visor a la PC.'},
                         {'tipo': 'repuesto', 'cantidad': 4, 'nombre': 'Pilas AA recargables', 'uso': 'Para los controles.'}],
            modos_uso=MODOS)
        cls.tipo = EquiposServicios.objects.create(codigo='COM-VR-01', nombre='Visor de prueba', familia=cls.familia,
                                                   accesorios_incluidos=[{'nombre': 'Controles táctiles', 'uso': 'Del modelo.', 'cantidad': 2}])
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de componentes', slug='lab-componentes', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='COM-VR-01-01', equipo=cls.tipo, laboratorio=cls.unidad,
                                                 version_sistema='v76.1', sistema_actualizado=date(2026, 9, 30))

    def test_las_cantidades_y_los_tipos_y_lo_de_la_familia_sin_repetir(self):
        self.assertEqual(accesorios_de(['2 × Controles | Para jugar', '3x Pilas', 'Estuche']),
                         [{'nombre': 'Controles', 'uso': 'Para jugar', 'cantidad': 2}, {'nombre': 'Pilas', 'uso': '', 'cantidad': 3},
                          {'nombre': 'Estuche', 'uso': '', 'cantidad': 1}])
        ficha = ficha_estandar(self.tipo)
        grupos = {grupo['clave']: grupo['items'] for grupo in ficha['componentes']}
        self.assertEqual([item['nombre'] for item in grupos['incluido']], ['Controles táctiles'])
        self.assertFalse(grupos['incluido'][0]['de_familia'], 'Lo del modelo manda; la familia no lo repite.')
        self.assertEqual(grupos['complementario'][0]['nombre'], 'Cable de enlace de 3 m')
        self.assertEqual(grupos['repuesto'][0]['cantidad'], 4)
        self.assertEqual([modo['nombre'] for modo in ficha['modos']], ['Autónomo', 'Conectado a una PC'])
        self.assertTrue(ficha['modos_de_familia'])
        EquiposServicios.objects.filter(pk=self.tipo.pk).update(modos_uso=MODOS[:1])
        self.tipo.refresh_from_db()
        self.assertEqual([modo['nombre'] for modo in ficha_estandar(self.tipo)['modos']], ['Autónomo'])

    def test_la_ficha_muestra_componentes_modos_sistema_y_videos(self):
        VideoEquipo.objects.create(familia=self.familia, url='https://youtu.be/eeeeeeeeeee', titulo='Primeros pasos')
        VideoEquipo.objects.create(familia=self.familia, url='https://youtu.be/fffffffffff', titulo='Conexión a PC')
        pagina = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, self.equipo.codigo_unidad]))
        for texto in ('Componentes y consumibles', 'Viene con el equipo', 'Complementos (no obligatorios)', 'Repuestos y consumibles',
                      '2×', 'Cómo funciona el equipo', 'data-modo="2"', 'Tarjeta gráfica NVIDIA RTX 3060 o superior',
                      'Sistema propio del visor.', 'v76.1', 'data-videos', 'data-elegir-video="fffffffffff"'):
            self.assertContains(pagina, texto)

    def test_los_consumibles_del_inventario_se_unen_a_los_repuestos_sin_repetir(self):
        from types import SimpleNamespace

        from apps.recursos.presentation.componentes_equipo import categoria_de, componentes_con_inventario

        grupos = ficha_estandar(self.tipo)['componentes']
        panos = SimpleNamespace(nombre='Pilas AA recargables', presentacion='Paquete de 4', codigo='INS-01', stock_total=8,
                                unidad_medida='unidad', imagen_publica_url='/static/pilas.jpg', icono='fas fa-battery-full',
                                get_clasificacion_display=lambda: 'Insumo')
        resultado = {grupo['clave']: grupo['items'] for grupo in
                     componentes_con_inventario(grupos, [SimpleNamespace(consumible=panos)], ['Paños de microfibra'],
                                                [{'url': '/media/correa.jpg', 'titulo': 'Controles táctiles'}])}
        repuestos = resultado['repuesto']
        self.assertEqual([item['nombre'] for item in repuestos], ['Pilas AA recargables', 'Paños de microfibra'],
                         'El repuesto de referencia con el mismo nombre que el insumo del inventario no se repite.')
        self.assertEqual((repuestos[0]['naturaleza'], repuestos[0]['existencia'], repuestos[0]['imagen']), ('consumible', 8, '/static/pilas.jpg'))
        self.assertFalse(repuestos[1]['en_inventario'])
        self.assertEqual(resultado['incluido'][0]['imagen'], '/media/correa.jpg', 'La foto del accesorio del modelo se usa por su título.')
        self.assertEqual(resultado['complementario'][0]['icono'], 'fas fa-plug')
        self.assertEqual(categoria_de('Procesador o plataforma'), ('Procesamiento', 'fas fa-microchip'))
        self.assertEqual(categoria_de('Autonomía de batería'), ('Energía', 'fas fa-bolt'))

    def test_el_cargador_de_familias_es_idempotente(self):
        datos = {'Visores de prueba': {
            'componentes': [('incluido', 1, 'Correa para la cabeza', 'Se ajusta antes de encender el visor.')],
            'modos': MODOS[:1], 'sistema': 'Sistema actualizado.'}}
        with mock.patch('apps.recursos.management.commands.cargar_componentes_familias.COMPONENTES', datos):
            salida = StringIO()
            call_command('cargar_componentes_familias', stdout=salida)
            self.assertIn('1 familias actualizadas', salida.getvalue())
            salida = StringIO()
            call_command('cargar_componentes_familias', stdout=salida)
            self.assertIn('0 familias actualizadas', salida.getvalue())
        self.familia.refresh_from_db()
        self.assertEqual(self.familia.componentes, [{'tipo': 'incluido', 'cantidad': 1, 'nombre': 'Correa para la cabeza',
                                                     'uso': 'Se ajusta antes de encender el visor.'}])
        self.assertEqual(self.familia.sistema, 'Sistema actualizado.')
