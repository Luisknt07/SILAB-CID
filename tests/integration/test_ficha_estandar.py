"""La ficha técnica estándar: las mismas secciones para todos los equipos, con lo que hay y lo que falta.

La plantilla del grupo de producto ordena las especificaciones; lo escrito como «Clave: valor» se aprovecha;
los accesorios llevan cómo se usan; los videos son los del modelo o, si no tiene, los de su familia; el público
ve lo registrado y quien gestiona ve qué tan completa está la ficha.
"""
from datetime import date
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.recursos.admin.equipos import FichaTecnicaForm
from apps.gestion_unidades.presentation.plantillas_ficha import accesorios_de, ficha_estandar, pares_de, youtube_id
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo, FotoEquipo, VideoEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class FichaEstandarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-ficha-estandar', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de fichas', slug='laboratorio-fichas', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.computo = FamiliaEquipo.objects.create(nombre='Estaciones de prueba', slug='estaciones-de-prueba', grupo='Cómputo')
        cls.tipo = EquiposServicios.objects.create(
            codigo='FIC-DIS-01', nombre='Workstation de diseño', familia=cls.computo, marca='HP', modelo='Z8 Fury G5',
            descripcion='Estación de trabajo para diseño.',
            caracteristicas_publicas='Procesador: Intel Xeon w5-3425\nMemoria: 256 GB DDR5\nColor de carcasa: negro',
            accesorios_incluidos=['Teclado', {'nombre': 'UPS de 3000 VA', 'uso': 'Enciéndela antes que el equipo'}])
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='FIC-DIS-01-01', equipo=cls.tipo, laboratorio=cls.unidad)

    def test_la_plantilla_del_grupo_ordena_y_aprovecha_lo_escrito(self):
        ficha = ficha_estandar(self.tipo, gestor=True)
        especificaciones = {item['clave']: item['valor'] for item in ficha['especificaciones']}
        self.assertEqual(ficha['grupo'], 'Cómputo')
        self.assertEqual(especificaciones['Procesador'], 'Intel Xeon w5-3425')
        self.assertEqual(especificaciones['Memoria RAM'], '256 GB DDR5')
        # Lo que la plantilla no nombra también se muestra.
        self.assertEqual(especificaciones['Color de carcasa'], 'negro')
        self.assertIn('Tarjeta gráfica', ficha['faltan'])
        self.assertEqual(ficha_estandar(self.tipo)['faltan'], [], 'El público no ve la lista de lo que falta.')
        self.assertEqual(ficha['incluye'], [{'nombre': 'Teclado', 'uso': '', 'cantidad': 1},
                                            {'nombre': 'UPS de 3000 VA', 'uso': 'Enciéndela antes que el equipo', 'cantidad': 1}])
        self.assertIn('Video de manejo', ficha['completitud']['falta'])
        self.assertEqual(self.tipo.get_accesorios_incluidos_list(), ['Teclado', 'UPS de 3000 VA'])

    def test_ayudantes_de_texto_accesorios_y_videos(self):
        self.assertEqual(pares_de('Procesador: Xeon / RAM: 64 GB / Silencioso'), ([('Procesador', 'Xeon'), ('RAM', '64 GB')], 'Silencioso'))
        self.assertEqual(accesorios_de(['Monitor | Por DisplayPort']), [{'nombre': 'Monitor', 'uso': 'Por DisplayPort', 'cantidad': 1}])
        self.assertEqual(youtube_id('https://youtu.be/abcdefghijk'), 'abcdefghijk')
        self.assertEqual(youtube_id('https://www.youtube.com/watch?v=abcdefghijk&t=3'), 'abcdefghijk')
        with self.assertRaises(ValidationError):
            VideoEquipo(url='https://vimeo.com/1', titulo='X', equipo=self.tipo).full_clean()
        with self.assertRaises(ValidationError):
            VideoEquipo(url='https://youtu.be/abcdefghijk', titulo='X').full_clean()

    def test_los_videos_de_la_familia_valen_si_el_modelo_no_tiene_propios(self):
        VideoEquipo.objects.create(familia=self.computo, url='https://youtu.be/aaaaaaaaaaa', titulo='Tutorial de la familia')
        self.assertEqual([video['id'] for video in ficha_estandar(self.tipo)['videos']], ['aaaaaaaaaaa'])
        VideoEquipo.objects.create(equipo=self.tipo, url='https://youtu.be/bbbbbbbbbbb', titulo='Tutorial del modelo')
        self.assertEqual([video['id'] for video in ficha_estandar(self.tipo)['videos']], ['bbbbbbbbbbb'])

    def test_el_administrador_guarda_las_especificaciones_y_los_accesorios_con_su_uso(self):
        formulario = FichaTecnicaForm(instance=self.tipo)
        self.assertEqual(formulario.fields['espec_0'].label, 'Procesador')
        self.assertEqual(formulario.fields['espec_0'].initial, 'Intel Xeon w5-3425')
        datos = {campo: valor for campo, valor in formulario.initial.items() if valor is not None and not isinstance(valor, (list, dict))}
        datos.update({'codigo': self.tipo.codigo, 'nombre': self.tipo.nombre, 'estado': 'disponible', 'rol': 'principal',
                      'cantidad': 1, 'espec_0': 'Intel Xeon w5-3425 de 12 núcleos', 'espec_3': 'NVIDIA RTX A4000 de 16 GB',
                      'otras_especificaciones': 'Color de carcasa: negro',
                      'accesorios_incluidos_texto': 'Monitor de 27 pulgadas | Por DisplayPort\nTeclado y mouse',
                      'accesorios_opcionales_texto': '', 'familia': self.computo.pk})
        formulario = FichaTecnicaForm(data=datos, instance=self.tipo)
        self.assertTrue(formulario.is_valid(), formulario.errors)
        tipo = formulario.save()
        self.assertEqual(tipo.especificaciones['Procesador'], 'Intel Xeon w5-3425 de 12 núcleos')
        self.assertEqual(tipo.especificaciones['Tarjeta gráfica'], 'NVIDIA RTX A4000 de 16 GB')
        self.assertEqual(tipo.especificaciones['Color de carcasa'], 'negro')
        self.assertEqual(tipo.accesorios_incluidos[0], {'nombre': 'Monitor de 27 pulgadas', 'uso': 'Por DisplayPort', 'cantidad': 1})

    def test_la_ficha_publica_muestra_las_secciones_y_la_completitud_solo_a_quien_gestiona(self):
        FotoEquipo.objects.create(equipo=self.tipo, imagen_catalogo='img/equipo.png', titulo='UPS', tipo='accesorio')
        VideoEquipo.objects.create(equipo=self.tipo, url='https://youtu.be/ccccccccccc', titulo='Cómo encenderla')
        url = reverse('ficha_equipo_publica', args=[self.unidad.slug, 'FIC-DIS-01-01'])
        publica = self.client.get(url)
        for texto in ('id="descripcion"', 'id="especificaciones"', 'Intel Xeon w5-3425', 'id="componentes"',
                      'Enciéndela antes que el equipo', 'equipo__miniaturas', 'data-video="ccccccccccc"'):
            self.assertContains(publica, texto)
        self.assertNotContains(publica, 'equipo__completitud')
        # El modelo en grande; cada unidad se elige dentro de la identificación, con su panel ya en la página
        # (oculto hasta elegirla) y su ficha como enlace; la hoja de especificaciones va antes que la descripción.
        otra = UnidadEquipo.objects.create(codigo_unidad='FIC-DIS-01-02', equipo=self.tipo, laboratorio=self.unidad)
        publica = self.client.get(url)
        contenido = publica.content.decode('utf-8')
        self.assertContains(publica, 'HP Z8 Fury G5')
        self.assertContains(publica, 'Unidad 1 de 2')
        self.assertContains(publica, f'data-registro="{otra.codigo_unidad}" hidden')
        self.assertIn(reverse('ficha_equipo_publica', args=[self.unidad.slug, otra.codigo_unidad]) + '#identidad', contenido)
        self.assertNotIn('id="unidades"', contenido)
        # El documento y los datos son para quien gestiona.
        self.assertNotIn('formato=pdf', contenido)
        self.assertNotIn('datos.csv', contenido)
        self.assertLess(contenido.index('id="identidad"'), contenido.index('class="equipo__hoja"'))
        self.assertLess(contenido.index('class="equipo__hoja"'), contenido.index('id="descripcion"'))
        # Sin marca ni modelo, el nombre grande es el modelo de referencia de la ficha.
        EquiposServicios.objects.filter(pk=self.tipo.pk).update(marca='', modelo='', caracteristicas_publicas='Modelo de referencia: Meta Quest 3')
        self.assertContains(self.client.get(url), 'Meta Quest 3')
        self.client.force_login(self.gestor)
        gestion = self.client.get(url).content.decode('utf-8')
        self.assertIn('equipo__completitud', gestion)
        # Un solo botón para el documento: la descarga está dentro del visor.
        self.assertIn('data-ver-pdf', gestion)
        self.assertEqual(gestion.count('formato=pdf&amp;descargar=1'), 1)
        self.assertIn('datos.csv', gestion)
        # Los códigos de inventario de cada unidad están en su panel, no en una sección aparte al final.
        self.assertEqual(gestion.count('Código de barras y QR'), 2)
        self.assertLess(gestion.index('Código de barras y QR'), gestion.index('id="especificaciones"'))

    def test_cargar_medios_de_familia_da_videos_y_foto_sin_pisar_lo_propio(self):
        medios = {'Estaciones de prueba': {'videos': [('https://www.youtube.com/watch?v=ddddddddddd', 'Tutorial', 'Canal', 'es')],
                                           'foto': ('img/catalogo/familias/estaciones.jpg', 'Autor · CC BY 4.0', 'https://commons.org/x')}}
        con_foto = EquiposServicios.objects.create(codigo='FIC-DIS-02', nombre='Otra estación', familia=self.computo,
                                                   imagen_catalogo='img/propia.png')
        texto = 'Qué es.\n\nCómo se usa.'
        with mock.patch('apps.recursos.management.commands.cargar_medios_familias.MEDIOS', medios), \
                mock.patch('apps.recursos.management.commands.cargar_medios_familias.DESCRIPCIONES', {'Estaciones de prueba': texto}):
            call_command('cargar_medios_familias', stdout=StringIO())
            call_command('cargar_medios_familias', stdout=StringIO())
        self.assertEqual(VideoEquipo.objects.filter(familia=self.computo).count(), 1)
        self.tipo.refresh_from_db()
        con_foto.refresh_from_db()
        self.assertEqual(self.tipo.imagen_catalogo, 'img/catalogo/familias/estaciones.jpg')
        self.assertTrue(self.tipo.credito_imagen.startswith('Foto del tipo de equipo'))
        self.assertEqual(con_foto.imagen_catalogo, 'img/propia.png')
        self.computo.refresh_from_db()
        self.assertEqual(self.computo.descripcion, texto)
        self.assertEqual(ficha_estandar(self.tipo)['descripcion_familia'], texto)
