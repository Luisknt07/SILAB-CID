"""Las fichas distinguen propuestas de existencias y agrupan un modelo una sola vez."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.presentation.area_unidad import equipos_de_ficha, ficha_de
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.recursos.models.unidades import UnidadEquipo


class AgruparEquiposDeFichaTests(SimpleTestCase):
    def setUp(self):
        self.modelo = EquiposServicios(
            pk=10, nombre='Impresora 3D FDM', marca='Bambu Lab', modelo='X1 Carbon',
            caracteristicas_publicas='Volumen: 256 × 256 × 256 mm',
            especificaciones={'Volumen': '256 mm por lado', 'Materiales': 'PLA, PETG'},
            instrucciones_publicas='Revisar la placa antes de imprimir.',
        )
        self.modelo.consumibles_del_area = [
            SimpleNamespace(consumible=SimpleNamespace(nombre='Filamento PLA', unidad_id=None)),
            SimpleNamespace(consumible=SimpleNamespace(nombre='Existencia de otra unidad', unidad_id=99)),
        ]
        self.activo = UnidadEquipo(pk=20, equipo=self.modelo, codigo_unidad='IMP-01', estado_unidad='disponible')
        self.otro = UnidadEquipo(pk=21, equipo=self.modelo, codigo_unidad='IMP-02', estado_unidad='dañado')

    def elemento(self, pk, nombre, **datos):
        return ElementoFichaArea(
            pk=pk, ficha_id=30, tipo='equipo', nombre=nombre, registrado=self.activo,
            ejemplo='Prusa i3 MK3', especificaciones='Volumen: 250 × 210 × 210 mm',
            cantidad='999 propuestas', **datos,
        )

    def test_puestos_del_mismo_modelo_no_duplican_activos_y_conservan_zonas_e_ids(self):
        primero = self.elemento(40, 'Puesto 1')
        segundo = self.elemento(41, 'Puesto 2')
        zonas = [{'equipos': ['Puesto 1']}, {'equipos': ['Puesto 2']}]

        filas = equipos_de_ficha([primero, segundo], [self.activo, self.activo, self.otro], zonas)

        self.assertEqual(len(filas), 1)
        fila = filas[0]
        self.assertEqual([x.pk for x in fila.unidades], [20, 21])
        self.assertEqual(fila.disponibles, 1)
        self.assertEqual(fila.zonas, [0, 1])
        self.assertEqual(fila.elementos_origen, [{'id': 40, 'nombre': 'Puesto 1'}, {'id': 41, 'nombre': 'Puesto 2'}])
        self.assertEqual(primero.nombre, 'Puesto 1')
        self.assertEqual(primero.ejemplo, 'Prusa i3 MK3')
        self.assertFalse(hasattr(primero, 'unidades'))

    def test_modelo_real_prevalece_sobre_ejemplos_de_otra_marca(self):
        fila = equipos_de_ficha([self.elemento(40, 'Puesto Prusa')], [self.activo], [])[0]

        self.assertEqual(fila.nombre, self.modelo.nombre)
        self.assertEqual(fila.modelo_mostrado, 'Bambu Lab · X1 Carbon')
        self.assertEqual(dict(fila.especificaciones_mostradas)['Volumen'], '256 mm por lado')
        self.assertEqual(fila.consumibles_mostrados, ['Filamento PLA'])
        self.assertEqual(fila.cuidados_mostrados, ['Revisar la placa antes de imprimir.'])
        self.assertNotIn('Prusa', str(fila.especificaciones_mostradas))

    def test_propuesta_con_vinculo_no_acredita_existencias_ni_se_mezcla_con_adquiridos(self):
        propuesta = self.elemento(42, 'Ampliación propuesta', solo_referencia=True)
        filas = equipos_de_ficha([self.elemento(40, 'Puesto 1'), propuesta], [self.activo], [])

        self.assertEqual(len(filas), 2)
        fila = next(x for x in filas if x.solo_referencia)
        self.assertEqual(fila.unidades, [])
        self.assertEqual(fila.disponibles, 0)
        self.assertFalse(fila.modelo_registrado)
        html = render_to_string('portal/pages/unidades/detalle/includes/existencia_equipo_ficha.html', {'equipo': fila})
        self.assertIn('Propuesta por evaluar · no adquirida', html)
        self.assertIn('Cantidad propuesta (referencial):', html)
        self.assertIn('999 propuestas', html)
        self.assertNotIn('disponible', html)

    def test_referencia_sin_bandera_no_se_declara_no_adquirida(self):
        referencia = ElementoFichaArea(pk=43, ficha_id=30, tipo='equipo', nombre='Referencia', cantidad='3 sugeridas')
        fila = equipos_de_ficha([referencia], [self.activo], [])[0]
        html = render_to_string('portal/pages/unidades/detalle/includes/existencia_equipo_ficha.html', {'equipo': fila})
        self.assertIn('Existencia por verificar', html)
        self.assertIn('Cantidad de referencia:', html)
        self.assertNotIn('no adquirida', html)
        self.assertFalse(fila.unidades)

    def test_el_mismo_modelo_en_fichas_distintas_no_se_fusiona(self):
        otra = self.elemento(41, 'Otra ficha')
        otra.ficha_id = 31
        self.assertEqual(len(equipos_de_ficha([self.elemento(40, 'Puesto 1'), otra], [self.activo], [])), 2)

    def test_no_reutiliza_especificaciones_antiguas_si_el_modelo_real_no_tiene_datos(self):
        self.modelo.especificaciones = {}
        self.modelo.caracteristicas_publicas = ''
        fila = equipos_de_ficha([self.elemento(40, 'Puesto Prusa')], [self.activo], [])[0]
        self.assertEqual(fila.especificaciones_mostradas, [])

    def test_ficha_individual_de_propuesta_rotula_cantidad_como_referencial(self):
        html = render_to_string('portal/pages/unidades/aula/includes/equipo_referencia_identidad.html', {
            'detalle': {'es_propuesta': True, 'cantidad_referencia': '2 equipos'},
            'elemento': {'ejemplo': 'Modelo por evaluar'},
        })
        self.assertIn('Propuesta por evaluar · no adquirida', html)
        self.assertIn('Cantidad propuesta (referencial)', html)
        self.assertNotIn('Cantidad instalada', html)


class FichaAreaPropuestasIntegracionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Unidad fichas sin duplicación', slug='fichas-sin-duplicacion', dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='FICHA-AREA-01', nombre='Impresión', activo=True)
        cls.ficha = FichaArea.objects.create(espacio=cls.area, publicada=True, distribucion='Zona 1 | Fabricar | Puesto 1\nZona 2 | Fabricar | Puesto 2')
        cls.modelo = EquiposServicios.objects.create(codigo='FICHA-MOD-01', nombre='Impresora FDM', marca='Bambu Lab', modelo='X1 Carbon', especificaciones={'Volumen': '256 mm por lado'})
        cls.activo = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='FICHA-ACT-01', estado_unidad='disponible')
        cls.area.equipos_asociados.add(cls.activo)
        for indice in range(1, 3):
            ElementoFichaArea.objects.create(ficha=cls.ficha, tipo='equipo', nombre=f'Puesto {indice}', registrado=cls.activo, ejemplo='Prusa antigua')
        cls.propuesta = ElementoFichaArea.objects.create(ficha=cls.ficha, tipo='equipo', nombre='Propuesta de ampliación', registrado=cls.activo, solo_referencia=True, cantidad='2 equipos')
        ajena = Unidad.objects.create(nombre='Unidad ajena', slug='fichas-unidad-ajena', dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        for unidad, codigo, nombre in ((cls.unidad, 'FICHA-CONS-01', 'PLA propio'), (ajena, 'FICHA-CONS-02', 'Resina ajena')):
            consumible = Consumible.objects.create(unidad=unidad, codigo=codigo, nombre=nombre)
            ConsumiblePorEquipo.objects.create(equipo=cls.modelo, consumible=consumible)

    def test_ficha_agrupa_sin_modificar_registros_y_precarga_relaciones(self):
        with patch('apps.gestion_unidades.presentation.area_unidad.visibles_para', side_effect=lambda elementos, *_: elementos):
            contenido = ficha_de(self.area, True, [self.activo])
        # La propuesta no existe en la unidad: la página del área no la muestra.
        self.assertEqual(contenido['total_equipos'], 1)
        self.assertFalse(any(equipo.solo_referencia for equipo in contenido['equipos']))
        real = next(x for x in contenido['equipos'] if x.modelo_registrado)
        self.assertEqual(len(real.unidades), 1)
        self.assertEqual(real.zonas, [0, 1])
        with self.assertNumQueries(0):
            self.assertEqual(real.consumibles_mostrados, ['PLA propio'])
            self.assertEqual(real.modelo_mostrado, 'Bambu Lab · X1 Carbon')
        self.assertEqual(ElementoFichaArea.objects.filter(ficha=self.ficha).count(), 3)
        self.assertEqual(ElementoFichaArea.objects.get(pk=real.pk).ejemplo, 'Prusa antigua')

    def test_ficha_individual_no_redirige_propuesta_con_fk_a_un_activo(self):
        url = reverse('ficha_equipo_referencia', args=[self.unidad.slug, self.propuesta.pk])
        with patch('apps.recursos.presentation.equipo_referencia.objeto_visible_para', return_value=True), patch(
            'apps.recursos.presentation.equipo_referencia.visibles_para', side_effect=lambda elementos, *_: elementos,
        ):
            # Al público no se le muestra una propuesta: no existe en la unidad.
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.force_login(get_user_model().objects.create_superuser('gestor-propuestas', 'g@example.org', 'clave'))
            pagina = self.client.get(url)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Propuesta por evaluar · no adquirida')
        self.assertContains(pagina, 'Cantidad propuesta (referencial)')
        self.assertNotContains(pagina, 'Cantidad instalada')
